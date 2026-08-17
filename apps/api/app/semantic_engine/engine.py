from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.observation import Observation
from app.models.semantic import SemanticConcept, SemanticRun
from app.semantic_engine.resolver import extract_concepts

EXTRACTOR_VERSION = "1.0"


def recompute_semantics(db: Session, hours: int = 24 * 30) -> dict:
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    observations = list(db.scalars(
        select(Observation).where(Observation.observed_at >= start).order_by(Observation.observed_at)
    ))
    run = SemanticRun(
        status="running",
        started_at=datetime.now(timezone.utc),
        observation_count=len(observations),
        metadata_json={"window_hours": hours, "extractor_version": EXTRACTOR_VERSION},
    )
    db.add(run)
    db.flush()
    created = 0
    try:
        for observation in observations:
            concepts = extract_concepts(observation.topic, observation.payload, observation.source, observation.metric)
            for concept in concepts:
                exists = db.scalar(select(SemanticConcept.id).where(
                    SemanticConcept.observation_id == observation.id,
                    SemanticConcept.canonical_key == concept.canonical_key,
                    SemanticConcept.extractor_version == EXTRACTOR_VERSION,
                ))
                if exists:
                    continue
                db.add(SemanticConcept(
                    observation_id=observation.id,
                    canonical_name=concept.canonical_name,
                    canonical_key=concept.canonical_key,
                    kind=concept.kind,
                    mention_text=concept.mention_text,
                    confidence=concept.confidence,
                    method=concept.method,
                    extractor_version=EXTRACTOR_VERSION,
                    attributes={**concept.attributes, "semantic_run_id": run.id},
                ))
                created += 1
        db.flush()
        run.concept_count = created
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
        "concepts_created": run.concept_count,
        "error": run.error,
    }


def latest_concepts(db: Session, limit: int = 500, kind: str | None = None, canonical_key: str | None = None):
    statement = select(SemanticConcept)
    if kind:
        statement = statement.where(SemanticConcept.kind == kind)
    if canonical_key:
        statement = statement.where(SemanticConcept.canonical_key == canonical_key)
    return list(db.scalars(statement.order_by(SemanticConcept.created_at.desc()).limit(limit)))


def semantic_summary(db: Session) -> dict:
    concept_count = db.scalar(select(func.count()).select_from(SemanticConcept)) or 0
    subject_count = db.scalar(select(func.count(func.distinct(SemanticConcept.canonical_key)))) or 0
    kind_rows = db.execute(
        select(SemanticConcept.kind, func.count(SemanticConcept.id))
        .group_by(SemanticConcept.kind)
        .order_by(func.count(SemanticConcept.id).desc())
    ).all()
    method_rows = db.execute(
        select(SemanticConcept.method, func.count(SemanticConcept.id))
        .group_by(SemanticConcept.method)
        .order_by(func.count(SemanticConcept.id).desc())
    ).all()
    last_run = db.scalar(select(SemanticRun).order_by(SemanticRun.started_at.desc()).limit(1))
    return {
        "concepts": concept_count,
        "subjects": subject_count,
        "kinds": [{"kind": kind, "count": count} for kind, count in kind_rows],
        "methods": [{"method": method, "count": count} for method, count in method_rows],
        "last_run": last_run,
    }


def concepts_by_observation(db: Session, observation_ids: list[str]) -> dict[str, list[SemanticConcept]]:
    if not observation_ids:
        return {}
    rows = list(db.scalars(select(SemanticConcept).where(SemanticConcept.observation_id.in_(observation_ids))))
    result: dict[str, list[SemanticConcept]] = defaultdict(list)
    for row in rows:
        result[row.observation_id].append(row)
    return result
