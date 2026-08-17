from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - registers all tables
from app.db.base import Base
from app.discovery_engine.engine import promote_candidate
from app.models.discovery import DiscoveryCandidate
from app.models.investigation import Investigation
from app.models.kernel import KernelEvent
from app.models.observation import Observation


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_watch_candidate(db: Session) -> DiscoveryCandidate:
    observation = Observation(
        source="demo",
        source_ref="running-clubs-1",
        topic="running clubs",
        metric="mentions",
        value=1.0,
        observed_at=datetime.now(timezone.utc),
        payload={},
        content_hash="a" * 64,
    )
    db.add(observation)
    db.flush()
    candidate = DiscoveryCandidate(
        canonical_key="running clubs",
        title="Running Clubs",
        status="watch",
        score=0.64,
        confidence=0.91,
        detector_count=3,
        evidence_count=1,
        summary="Demo candidate",
        detector_scores={"velocity": 0.5},
        evidence_ids=[observation.id],
        attributes={"quality_gate": {"status": "watch", "reasons": ["fewer than 2 independent sources"]}},
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def test_watch_candidate_still_blocks_normal_promotion():
    db = make_session()
    candidate = seed_watch_candidate(db)
    with pytest.raises(ValueError, match="WATCH"):
        promote_candidate(db, candidate.id)


def test_manual_override_requires_reason():
    db = make_session()
    candidate = seed_watch_candidate(db)
    with pytest.raises(ValueError, match="requires a reason"):
        promote_candidate(db, candidate.id, allow_override=True)


def test_manual_override_creates_audited_investigation():
    db = make_session()
    candidate = seed_watch_candidate(db)
    investigation = promote_candidate(
        db,
        candidate.id,
        allow_override=True,
        override_reason="Local runtime testing",
    )
    assert investigation.slug == "running-clubs"
    assert investigation.status == "collecting"
    assert investigation.attributes["promotion"]["mode"] == "manual_override"
    assert investigation.attributes["promotion"]["original_status"] == "watch"
    assert investigation.attributes["promotion"]["override_reason"] == "Local runtime testing"
    event = db.scalar(select(KernelEvent).where(KernelEvent.event_type == "CandidatePromotionOverridden"))
    assert event is not None
    assert event.aggregate_id == investigation.id
    assert event.payload["candidate_id"] == candidate.id
    assert db.scalar(select(Investigation).where(Investigation.slug == "running-clubs")) is not None
