from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import math

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.knowledge_graph.resolver import ResolvedEntity, extract_known_entities, resolve_phrase
from app.models.entity import Entity
from app.models.feature import Feature
from app.models.graph import GraphRun
from app.models.observation import Observation
from app.models.relationship import Relationship
from app.models.semantic import SemanticConcept


def _entity(db: Session, resolved: ResolvedEntity) -> Entity:
    existing = db.scalar(select(Entity).where(Entity.canonical_key == resolved.canonical_key))
    if existing:
        aliases = list(dict.fromkeys([*existing.aliases, *resolved.aliases]))
        existing.aliases = aliases
        return existing
    item = Entity(
        kind=resolved.kind,
        canonical_name=resolved.canonical_name,
        canonical_key=resolved.canonical_key,
        aliases=list(resolved.aliases),
        attributes={"resolver": "canonical_v1"},
    )
    db.add(item)
    db.flush()
    return item


def _upsert_edge(
    db: Session,
    source: Entity,
    target: Entity,
    kind: str,
    evidence_id: str,
    observed_at: datetime,
    confidence: float,
    provenance: dict,
) -> Relationship:
    edge = db.scalar(
        select(Relationship).where(
            Relationship.source_entity_id == source.id,
            Relationship.target_entity_id == target.id,
            Relationship.kind == kind,
        )
    )
    if edge is None:
        edge = Relationship(
            source_entity_id=source.id,
            target_entity_id=target.id,
            kind=kind,
            confidence=confidence,
            evidence_ids=[evidence_id],
            first_seen=observed_at,
            last_seen=observed_at,
            provenance=provenance,
        )
        db.add(edge)
        return edge
    edge.evidence_ids = list(dict.fromkeys([*edge.evidence_ids, evidence_id]))
    edge.first_seen = min(filter(None, [edge.first_seen, observed_at]))
    edge.last_seen = max(filter(None, [edge.last_seen, observed_at]))
    # Confidence rises slowly as independent evidence accumulates but remains bounded.
    edge.confidence = min(0.99, max(edge.confidence, confidence) + min(0.15, 0.02 * (len(edge.evidence_ids) - 1)))
    edge.provenance = {**edge.provenance, **provenance, "evidence_count": len(edge.evidence_ids)}
    return edge


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _semantic_edges(db: Session, subject_entities: dict[str, Entity]) -> int:
    semantic = list(
        db.scalars(
            select(Feature)
            .where(Feature.feature_type == "semantic", Feature.name == "embedding")
            .order_by(Feature.computed_at.desc())
            .limit(1000)
        )
    )
    latest: dict[str, Feature] = {}
    for item in semantic:
        latest.setdefault(item.subject, item)
    subjects = list(latest)
    count = 0
    for i, left in enumerate(subjects):
        for right in subjects[i + 1 :]:
            score = _cosine(latest[left].vector, latest[right].vector)
            if score < 0.90:
                continue
            left_entity = subject_entities.get(left) or _entity(db, resolve_phrase(left))
            right_entity = subject_entities.get(right) or _entity(db, resolve_phrase(right))
            evidence_ids = list(dict.fromkeys([*latest[left].evidence_ids, *latest[right].evidence_ids]))
            if not evidence_ids:
                continue
            edge = db.scalar(
                select(Relationship).where(
                    Relationship.source_entity_id == left_entity.id,
                    Relationship.target_entity_id == right_entity.id,
                    Relationship.kind == "SEMANTICALLY_RELATED_TO",
                )
            )
            now = datetime.now(timezone.utc)
            if edge is None:
                db.add(Relationship(
                    source_entity_id=left_entity.id,
                    target_entity_id=right_entity.id,
                    kind="SEMANTICALLY_RELATED_TO",
                    confidence=min(0.95, score),
                    evidence_ids=evidence_ids,
                    first_seen=now,
                    last_seen=now,
                    provenance={"method": "semantic_fingerprint_cosine", "similarity": round(score, 4)},
                ))
                count += 1
    return count


def _graph_features(db: Session, run_id: str) -> int:
    entities = list(db.scalars(select(Entity)))
    edges = list(db.scalars(select(Relationship)))
    if not entities:
        return 0
    neighbors: dict[str, set[str]] = defaultdict(set)
    evidence_by_entity: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        neighbors[edge.source_entity_id].add(edge.target_entity_id)
        neighbors[edge.target_entity_id].add(edge.source_entity_id)
        evidence_by_entity[edge.source_entity_id].update(edge.evidence_ids)
        evidence_by_entity[edge.target_entity_id].update(edge.evidence_ids)
    max_degree = max((len(neighbors[e.id]) for e in entities), default=1) or 1

    component: dict[str, int] = {}
    component_id = 0
    for entity in entities:
        if entity.id in component:
            continue
        component_id += 1
        q = deque([entity.id])
        component[entity.id] = component_id
        while q:
            current = q.popleft()
            for other in neighbors[current]:
                if other not in component:
                    component[other] = component_id
                    q.append(other)

    now = datetime.now(timezone.utc)
    created = 0
    for entity in entities:
        degree = len(neighbors[entity.id])
        evidence_ids = sorted(evidence_by_entity[entity.id])
        rows = [
            ("degree", float(degree)),
            ("degree_centrality", degree / max_degree),
            ("community", float(component.get(entity.id, 0))),
        ]
        for name, value in rows:
            db.add(Feature(
                subject=entity.canonical_key,
                feature_type="graph",
                name=name,
                value=value,
                vector=[],
                window="current",
                extractor_id="knowledge_graph",
                extractor_version="1.0",
                confidence=1.0,
                evidence_ids=evidence_ids,
                attributes={"graph_run_id": run_id, "entity_id": entity.id, "entity_kind": entity.kind},
                computed_at=now,
            ))
            created += 1
    return created


def rebuild_graph(db: Session, hours: int = 24 * 30) -> dict:
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    observations = list(db.scalars(select(Observation).where(Observation.observed_at >= start).order_by(Observation.observed_at)))
    run = GraphRun(status="running", started_at=datetime.now(timezone.utc), observation_count=len(observations), metadata_json={"window_hours": hours})
    db.add(run)
    db.flush()
    try:
        subject_entities: dict[str, Entity] = {}
        for obs in observations:
            if not obs.topic:
                continue
            topic = _entity(db, resolve_phrase(obs.topic))
            subject_entities[obs.topic] = topic
            source = _entity(db, resolve_phrase(obs.source, default_kind="source"))
            metric = _entity(db, resolve_phrase(obs.metric, default_kind="metric"))
            _upsert_edge(db, topic, source, "OBSERVED_ON", obs.id, obs.observed_at, 0.98, {"method": "observation_source"})
            _upsert_edge(db, topic, metric, "MEASURED_BY", obs.id, obs.observed_at, 0.98, {"method": "observation_metric"})

            semantic_rows = list(db.scalars(select(SemanticConcept).where(SemanticConcept.observation_id == obs.id)))
            if semantic_rows:
                for concept in semantic_rows:
                    resolved = ResolvedEntity(concept.canonical_name, concept.canonical_key, concept.kind, ())
                    mentioned = _entity(db, resolved)
                    if mentioned.id != topic.id and concept.kind != "keyword":
                        _upsert_edge(
                            db, topic, mentioned, "MENTIONS", obs.id, obs.observed_at,
                            max(0.60, min(0.98, concept.confidence)),
                            {"method": "semantic_engine", "semantic_method": concept.method},
                        )
            else:
                text = " ".join(str(v) for v in [obs.topic, obs.payload.get("title", ""), obs.payload.get("text", ""), obs.payload.get("url", "")])
                for resolved in extract_known_entities(text):
                    mentioned = _entity(db, resolved)
                    if mentioned.id != topic.id:
                        _upsert_edge(db, topic, mentioned, "MENTIONS", obs.id, obs.observed_at, 0.86, {"method": "catalog_entity_extraction"})

        _semantic_edges(db, subject_entities)
        db.flush()
        run.entity_count = db.scalar(select(func.count()).select_from(Entity)) or 0
        run.relationship_count = db.scalar(select(func.count()).select_from(Relationship)) or 0
        run.feature_count = _graph_features(db, run.id)
        run.status = "succeeded"
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:4000]
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return {
        "run_id": run.id,
        "status": run.status,
        "observations": run.observation_count,
        "entities": run.entity_count,
        "relationships": run.relationship_count,
        "graph_features": run.feature_count,
        "error": run.error,
    }


def graph_summary(db: Session) -> dict:
    entity_count = db.scalar(select(func.count()).select_from(Entity)) or 0
    relationship_count = db.scalar(select(func.count()).select_from(Relationship)) or 0
    kind_rows = db.execute(select(Entity.kind, func.count(Entity.id)).group_by(Entity.kind).order_by(func.count(Entity.id).desc())).all()
    edge_rows = db.execute(select(Relationship.kind, func.count(Relationship.id)).group_by(Relationship.kind).order_by(func.count(Relationship.id).desc())).all()
    last_run = db.scalar(select(GraphRun).order_by(GraphRun.started_at.desc()).limit(1))
    return {
        "entities": entity_count,
        "relationships": relationship_count,
        "entity_kinds": [{"kind": kind, "count": count} for kind, count in kind_rows],
        "relationship_kinds": [{"kind": kind, "count": count} for kind, count in edge_rows],
        "last_run": last_run,
    }


def neighborhood(db: Session, entity_id: str, limit: int = 100) -> dict:
    root = db.get(Entity, entity_id)
    if root is None:
        raise KeyError(entity_id)
    edges = list(db.scalars(
        select(Relationship)
        .where(or_(Relationship.source_entity_id == entity_id, Relationship.target_entity_id == entity_id))
        .order_by(Relationship.confidence.desc())
        .limit(limit)
    ))
    ids = {entity_id}
    for edge in edges:
        ids.add(edge.source_entity_id)
        ids.add(edge.target_entity_id)
    entities = list(db.scalars(select(Entity).where(Entity.id.in_(ids))))
    return {"root": root, "entities": entities, "relationships": edges}
