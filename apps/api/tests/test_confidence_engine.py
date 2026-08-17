from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.investigation_runtime.confidence import calculate_confidence
from app.investigation_runtime.engine import (
    add_hypothesis,
    attach_hypothesis_evidence,
    confidence_history,
    recalculate_hypothesis_confidence,
)
from app.models.hypothesis import Hypothesis
from app.models.investigation import Investigation
from app.models.kernel import InvestigationRevision, KernelEvent
from app.models.observation import Observation


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed(db: Session):
    investigation = Investigation(
        title="Running Clubs",
        slug="running-clubs",
        status="under_review",
        confidence=0.91,
        summary="Running clubs are growing.",
        attributes={},
    )
    db.add(investigation)
    observations = []
    for index in range(3):
        item = Observation(
            source="demo" if index < 2 else "news",
            source_ref=f"obs-{index}",
            topic="running clubs",
            metric="mentions",
            value=1.0,
            observed_at=datetime.now(timezone.utc),
            payload={},
            content_hash=(str(index + 1) * 64)[:64],
        )
        db.add(item)
        observations.append(item)
    db.commit()
    db.refresh(investigation)
    for item in observations:
        db.refresh(item)
    hypothesis = add_hypothesis(
        db,
        investigation.id,
        title="Running clubs are becoming a lifestyle movement",
        confidence=0.62,
    )
    return investigation, hypothesis, observations


def test_confidence_math_is_deterministic_and_directional():
    base = calculate_confidence(prior=0.62, supporting_weight=0, contradicting_weight=0)
    support = calculate_confidence(prior=0.62, supporting_weight=2, contradicting_weight=0)
    contradict = calculate_confidence(prior=0.62, supporting_weight=0, contradicting_weight=2)
    assert round(base.posterior, 6) == 0.62
    assert support.posterior > base.posterior
    assert contradict.posterior < base.posterior
    assert support == calculate_confidence(prior=0.62, supporting_weight=2, contradicting_weight=0)


def test_supporting_evidence_increases_confidence_and_records_history():
    db = make_session()
    investigation, hypothesis, observations = seed(db)
    attach_hypothesis_evidence(
        db,
        investigation.id,
        hypothesis.id,
        observation_id=observations[0].id,
        stance="supporting",
        weight=1.0,
    )
    updated = db.get(Hypothesis, hypothesis.id)
    assert updated.confidence > 0.62
    history = confidence_history(db, investigation.id, hypothesis.id)
    assert len(history) == 1
    assert history[0].old_confidence == 0.62
    assert history[0].new_confidence == updated.confidence
    assert history[0].supporting_weight == 1.0
    events = list(db.scalars(select(KernelEvent).where(KernelEvent.aggregate_id == investigation.id)))
    assert any(event.event_type == "EvidenceLinked" for event in events)
    assert any(event.event_type == "HypothesisConfidenceChanged" for event in events)


def test_contradicting_evidence_can_reduce_confidence():
    db = make_session()
    investigation, hypothesis, observations = seed(db)
    attach_hypothesis_evidence(
        db,
        investigation.id,
        hypothesis.id,
        observation_id=observations[0].id,
        stance="contradicting",
        weight=2.0,
    )
    updated = db.get(Hypothesis, hypothesis.id)
    assert updated.confidence < 0.62


def test_recalculation_is_idempotent_for_same_evidence():
    db = make_session()
    investigation, hypothesis, observations = seed(db)
    attach_hypothesis_evidence(
        db,
        investigation.id,
        hypothesis.id,
        observation_id=observations[0].id,
        stance="supporting",
        weight=1.5,
    )
    once = db.get(Hypothesis, hypothesis.id).confidence
    recalculate_hypothesis_confidence(db, investigation.id, hypothesis.id)
    twice = db.get(Hypothesis, hypothesis.id).confidence
    assert once == twice


def test_confidence_commit_snapshots_hypothesis_state():
    db = make_session()
    investigation, hypothesis, observations = seed(db)
    attach_hypothesis_evidence(
        db,
        investigation.id,
        hypothesis.id,
        observation_id=observations[0].id,
        stance="supporting",
    )
    revision = db.scalar(
        select(InvestigationRevision)
        .where(InvestigationRevision.investigation_id == investigation.id)
        .order_by(InvestigationRevision.revision_number.desc())
        .limit(1)
    )
    assert revision is not None
    snapshot_hypothesis = next(item for item in revision.snapshot["hypotheses"] if item["id"] == hypothesis.id)
    assert snapshot_hypothesis["confidence"] > 0.62
    assert revision.snapshot["hypothesis_evidence"][0]["stance"] == "supporting"
