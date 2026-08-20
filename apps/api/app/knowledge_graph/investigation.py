from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge_graph.analytics import analyze_investigation_graph

from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.relationship import Relationship


def _node_id(kind: str, object_id: str) -> str:
    return f"{kind}:{object_id}"


def _stance_edge(stance: str) -> str:
    return {
        "supporting": "SUPPORTS",
        "contradicting": "CONTRADICTS",
        "neutral": "CONTEXT_FOR",
    }.get(stance, "CONTEXT_FOR")


def _connected_components(node_ids: list[str], edges: list[dict[str, Any]]) -> int:
    if not node_ids:
        return 0
    neighbors: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        neighbors[source].add(target)
        neighbors[target].add(source)
    seen: set[str] = set()
    components = 0
    for node_id in node_ids:
        if node_id in seen:
            continue
        components += 1
        queue = deque([node_id])
        seen.add(node_id)
        while queue:
            current = queue.popleft()
            for other in neighbors[current]:
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
    return components


def investigation_graph(db: Session, investigation_id: str) -> dict[str, Any]:
    """Build a deterministic, evidence-derived graph for one investigation.

    The returned graph is a projection. Canonical observations, hypotheses, and
    knowledge-graph relationships remain unchanged.
    """
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError(investigation_id)

    hypotheses = list(
        db.scalars(
            select(Hypothesis)
            .where(Hypothesis.investigation_id == investigation_id)
            .order_by(Hypothesis.created_at.asc())
        )
    )
    hypothesis_ids = [item.id for item in hypotheses]
    hypothesis_links: list[HypothesisEvidenceLink] = []
    if hypothesis_ids:
        hypothesis_links = list(
            db.scalars(
                select(HypothesisEvidenceLink)
                .where(HypothesisEvidenceLink.hypothesis_id.in_(hypothesis_ids))
                .order_by(HypothesisEvidenceLink.created_at.asc())
            )
        )

    investigation_links = list(
        db.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.investigation_id == investigation_id)
            .order_by(EvidenceLink.created_at.asc())
        )
    )
    observation_ids = {
        link.observation_id for link in investigation_links if link.observation_id
    }
    observation_ids.update(
        link.observation_id for link in hypothesis_links if link.observation_id
    )

    observations: list[Observation] = []
    if observation_ids:
        observations = list(
            db.scalars(
                select(Observation)
                .where(Observation.id.in_(observation_ids))
                .order_by(Observation.observed_at.asc())
            )
        )
    observation_by_id = {item.id: item for item in observations}

    relationships: list[Relationship] = []
    if observation_ids:
        # Relationship evidence is stored as JSON, so use a bounded in-memory
        # filter to preserve SQLite/Postgres portability in the reference build.
        relationships = [
            item
            for item in db.scalars(select(Relationship).order_by(Relationship.confidence.desc()))
            if set(item.evidence_ids or []).intersection(observation_ids)
        ]

    entity_ids: set[str] = set()
    for relationship in relationships:
        entity_ids.add(relationship.source_entity_id)
        entity_ids.add(relationship.target_entity_id)
    entities: list[Entity] = []
    if entity_ids:
        entities = list(db.scalars(select(Entity).where(Entity.id.in_(entity_ids))))
    entity_by_id = {item.id: item for item in entities}

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    inv_node = _node_id("investigation", investigation.id)
    nodes.append(
        {
            "id": inv_node,
            "domain_id": investigation.id,
            "kind": "investigation",
            "label": investigation.title,
            "description": investigation.summary,
            "confidence": investigation.confidence,
            "evidence_count": len(observations),
            "source_count": len({item.source for item in observations}),
            "metadata": {
                "status": investigation.status,
                "slug": investigation.slug,
            },
        }
    )

    for hypothesis in hypotheses:
        node_id = _node_id("hypothesis", hypothesis.id)
        related_links = [link for link in hypothesis_links if link.hypothesis_id == hypothesis.id]
        nodes.append(
            {
                "id": node_id,
                "domain_id": hypothesis.id,
                "kind": "hypothesis",
                "label": hypothesis.title,
                "description": hypothesis.description,
                "confidence": hypothesis.confidence,
                "evidence_count": len(related_links),
                "source_count": len(
                    {
                        observation_by_id[link.observation_id].source
                        for link in related_links
                        if link.observation_id in observation_by_id
                    }
                ),
                "metadata": {
                    "status": hypothesis.status,
                    "prior_confidence": hypothesis.prior_confidence,
                },
            }
        )
        edges.append(
            {
                "id": f"investigation-hypothesis:{hypothesis.id}",
                "source": inv_node,
                "target": node_id,
                "kind": "HAS_HYPOTHESIS",
                "confidence": 1.0,
                "evidence_ids": [link.observation_id for link in related_links],
                "metadata": {},
            }
        )

    for observation in observations:
        node_id = _node_id("observation", observation.id)
        nodes.append(
            {
                "id": node_id,
                "domain_id": observation.id,
                "kind": "observation",
                "label": f"{observation.source}: {observation.metric}",
                "description": observation.topic,
                "confidence": 1.0,
                "evidence_count": 1,
                "source_count": 1,
                "metadata": {
                    "source": observation.source,
                    "source_ref": observation.source_ref,
                    "metric": observation.metric,
                    "value": observation.value,
                    "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
                    "provenance": (observation.payload or {}).get("provenance", {}),
                },
            }
        )
        edges.append(
            {
                "id": f"investigation-observation:{observation.id}",
                "source": inv_node,
                "target": node_id,
                "kind": "HAS_EVIDENCE",
                "confidence": 1.0,
                "evidence_ids": [observation.id],
                "metadata": {"source": observation.source},
            }
        )

    for link in hypothesis_links:
        if link.observation_id not in observation_by_id:
            continue
        edges.append(
            {
                "id": f"hypothesis-evidence:{link.id}",
                "source": _node_id("observation", link.observation_id),
                "target": _node_id("hypothesis", link.hypothesis_id),
                "kind": _stance_edge(link.stance),
                "confidence": max(0.0, min(1.0, link.weight)),
                "evidence_ids": [link.observation_id],
                "metadata": {
                    "stance": link.stance,
                    "weight": link.weight,
                    "rationale": link.rationale,
                },
            }
        )

    evidence_by_entity: dict[str, set[str]] = defaultdict(set)
    relationship_count_by_entity: dict[str, int] = defaultdict(int)
    for relationship in relationships:
        evidence_by_entity[relationship.source_entity_id].update(relationship.evidence_ids or [])
        evidence_by_entity[relationship.target_entity_id].update(relationship.evidence_ids or [])
        relationship_count_by_entity[relationship.source_entity_id] += 1
        relationship_count_by_entity[relationship.target_entity_id] += 1

    for entity in entities:
        evidence_ids = sorted(evidence_by_entity[entity.id].intersection(observation_ids))
        source_count = len(
            {
                observation_by_id[evidence_id].source
                for evidence_id in evidence_ids
                if evidence_id in observation_by_id
            }
        )
        nodes.append(
            {
                "id": _node_id("entity", entity.id),
                "domain_id": entity.id,
                "kind": entity.kind or "entity",
                "label": entity.canonical_name,
                "description": entity.description,
                "confidence": 1.0,
                "evidence_count": len(evidence_ids),
                "source_count": source_count,
                "metadata": {
                    "canonical_key": entity.canonical_key,
                    "aliases": entity.aliases,
                    "attributes": entity.attributes,
                    "relationship_count": relationship_count_by_entity[entity.id],
                },
            }
        )

        for evidence_id in evidence_ids:
            edges.append(
                {
                    "id": f"observation-entity:{evidence_id}:{entity.id}",
                    "source": _node_id("observation", evidence_id),
                    "target": _node_id("entity", entity.id),
                    "kind": "EVIDENCES_ENTITY",
                    "confidence": 1.0,
                    "evidence_ids": [evidence_id],
                    "metadata": {},
                }
            )

    for relationship in relationships:
        relevant_evidence = sorted(set(relationship.evidence_ids or []).intersection(observation_ids))
        if not relevant_evidence:
            continue
        edges.append(
            {
                "id": f"relationship:{relationship.id}",
                "source": _node_id("entity", relationship.source_entity_id),
                "target": _node_id("entity", relationship.target_entity_id),
                "kind": relationship.kind,
                "confidence": relationship.confidence,
                "evidence_ids": relevant_evidence,
                "metadata": {
                    "first_seen": relationship.first_seen.isoformat() if relationship.first_seen else None,
                    "last_seen": relationship.last_seen.isoformat() if relationship.last_seen else None,
                    "provenance": relationship.provenance,
                },
            }
        )

    # Degree is deliberately calculated on the investigation projection, not on
    # the global graph. This makes the metric scientifically scoped and replayable.
    degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    max_degree = max(degree.values(), default=1) or 1
    for node in nodes:
        node["degree"] = degree[node["id"]]
        node["degree_centrality"] = round(degree[node["id"]] / max_degree, 6)

    node_ids = [node["id"] for node in nodes]
    components = _connected_components(node_ids, edges)
    possible_edges = len(nodes) * (len(nodes) - 1) / 2
    density = (len(edges) / possible_edges) if possible_edges else 0.0
    sources = sorted({item.source for item in observations})

    projection = {
        "investigation": {
            "id": investigation.id,
            "title": investigation.title,
            "status": investigation.status,
        },
        "nodes": nodes,
        "edges": edges,
        "metrics": {
            "nodes": len(nodes),
            "edges": len(edges),
            "entities": len(entities),
            "observations": len(observations),
            "hypotheses": len(hypotheses),
            "independent_sources": len(sources),
            "sources": sources,
            "connected_components": components,
            "density": round(density, 6),
            "relationship_types": dict(
                sorted(
                    {
                        kind: sum(1 for edge in edges if edge["kind"] == kind)
                        for kind in {edge["kind"] for edge in edges}
                    }.items()
                )
            ),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "derived": True,
    }

    projection["analytics"] = analyze_investigation_graph(projection)
    return projection
