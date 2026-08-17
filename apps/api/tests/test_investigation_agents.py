from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent_orchestration.engine import refresh_investigation, run_agent
from app.db.base import Base
from app.models.agent import AgentFinding
from app.models.evidence import EvidenceLink
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.kernel import KernelEvent


def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def add_observation(db, *, source="demo", source_ref="running-clubs-search", metric="search_interest", value=52.0):
    item = Observation(
        source=source,
        source_ref=source_ref,
        topic="running clubs",
        metric=metric,
        value=value,
        observed_at=datetime.now(timezone.utc),
        content_hash=f"{source}-{source_ref}-{metric}-{value}",
        payload={"demo": source == "demo"},
    )
    db.add(item)
    db.flush()
    return item


def test_evidence_agent_flags_source_diversity_and_repetition():
    db = db_session()
    inv = Investigation(title="Running Clubs", slug="running-clubs", status="under_review", confidence=0.9, attributes={"semantic_kind": "behavior"})
    db.add(inv); db.flush()
    a = add_observation(db, value=52.0)
    b = add_observation(db, value=53.0)
    db.add_all([EvidenceLink(investigation_id=inv.id, observation_id=a.id), EvidenceLink(investigation_id=inv.id, observation_id=b.id)])
    db.commit()

    task = run_agent(db, agent_id="evidence_agent", task_type="AUDIT_INVESTIGATION_EVIDENCE", target_type="investigation", target_id=inv.id)
    assert task.status == "completed"
    assert task.result_json["independent_sources"] == 1
    assert task.result_json["repeated_observations"] == 1
    categories = {row.category for row in db.query(AgentFinding).filter(AgentFinding.task_id == task.id).all()}
    assert "source_diversity" in categories
    assert "evidence_repetition" in categories
    assert "missing_sources" in categories
    event_types = [row.event_type for row in db.query(KernelEvent).filter(KernelEvent.aggregate_id == inv.id).all()]
    assert "AgentRunStarted" in event_types
    assert "AgentFindingCreated" in event_types
    assert "AgentRunCompleted" in event_types


def test_refresh_recalculates_without_compounding_confidence():
    db = db_session()
    inv = Investigation(title="Running Clubs", slug="running-clubs", status="under_review", confidence=0.9)
    db.add(inv); db.flush()
    obs = add_observation(db)
    db.add(EvidenceLink(investigation_id=inv.id, observation_id=obs.id))
    hypothesis = Hypothesis(investigation_id=inv.id, title="Lifestyle movement", prior_confidence=0.62, confidence=0.696)
    db.add(hypothesis); db.flush()
    db.add(HypothesisEvidenceLink(hypothesis_id=hypothesis.id, observation_id=obs.id, stance="supporting", weight=1.0))
    db.commit()

    result = refresh_investigation(db, inv.id)
    assert result["confidence_updates"][0]["new_confidence"] == 0.696
    assert result["confidence_updates"][0]["changed"] is False
    refreshed = db.get(Hypothesis, hypothesis.id)
    assert refreshed.confidence == 0.696
    event_types = [row.event_type for row in db.query(KernelEvent).filter(KernelEvent.aggregate_id == inv.id).all()]
    assert "HypothesisRecalculated" in event_types
    assert "InvestigationRefreshed" in event_types
