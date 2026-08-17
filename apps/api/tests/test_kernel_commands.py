from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.kernel import KernelCommand, execute_command
from app.models.hypothesis import Hypothesis
from app.models.investigation import Investigation
from app.models.kernel import KernelCommandLog, KernelEvent
from app.models.observation import Observation


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_hypothesis_runs_through_command_log_and_correlates_events():
    db = make_session()
    inv = Investigation(title="Running Clubs", slug="running-clubs", status="collecting", confidence=0.91, attributes={})
    db.add(inv); db.commit(); db.refresh(inv)
    command = KernelCommand(
        command_type="CreateHypothesis",
        aggregate_type="investigation",
        aggregate_id=inv.id,
        payload={"title": "Lifestyle movement", "confidence": 0.62},
        correlation_id="corr-001",
    )
    result = execute_command(db, command)
    assert result.title == "Lifestyle movement"
    log = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == command.id))
    assert log is not None
    assert log.status == "completed"
    assert log.correlation_id == "corr-001"
    event = db.scalar(
        select(KernelEvent)
        .where(KernelEvent.aggregate_id == inv.id, KernelEvent.event_type == "HypothesisAdded")
        .limit(1)
    )
    assert event is not None
    assert event.metadata_json["command_id"] == command.id
    assert event.metadata_json["correlation_id"] == "corr-001"
    assert event.metadata_json["command_type"] == "CreateHypothesis"


def test_failed_command_is_audited():
    db = make_session()
    command = KernelCommand(
        command_type="CreateHypothesis",
        aggregate_type="investigation",
        aggregate_id="missing-investigation",
        payload={"title": "Will fail", "confidence": 0.5},
    )
    try:
        execute_command(db, command)
    except KeyError:
        pass
    else:
        raise AssertionError("Expected missing investigation failure")
    log = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == command.id))
    assert log is not None
    assert log.status == "failed"
    assert log.error


def test_link_evidence_command_propagates_correlation_to_nested_events():
    db = make_session()
    inv = Investigation(title="Running Clubs", slug="running-clubs", status="under_review", confidence=0.91, attributes={})
    db.add(inv); db.flush()
    hypothesis = Hypothesis(investigation_id=inv.id, title="Lifestyle", prior_confidence=0.62, confidence=0.62)
    observation = Observation(
        source="demo", source_ref="run", topic="running clubs", metric="mentions", value=1.0,
        observed_at=datetime.now(timezone.utc), payload={}, content_hash="a" * 64,
    )
    db.add_all([hypothesis, observation]); db.commit(); db.refresh(inv); db.refresh(hypothesis); db.refresh(observation)
    command = KernelCommand(
        command_type="LinkHypothesisEvidence",
        aggregate_type="investigation",
        aggregate_id=inv.id,
        payload={
            "hypothesis_id": hypothesis.id,
            "observation_id": observation.id,
            "stance": "supporting",
            "weight": 1.0,
        },
        correlation_id="corr-evidence",
        causation_id="parent-command",
    )
    execute_command(db, command)
    events = list(db.scalars(select(KernelEvent).where(KernelEvent.aggregate_id == inv.id)))
    correlated = [e for e in events if e.metadata_json.get("command_id") == command.id]
    assert {e.event_type for e in correlated} >= {"EvidenceLinked", "HypothesisConfidenceChanged", "InvestigationCommitted"}
    assert all(e.metadata_json.get("correlation_id") == "corr-evidence" for e in correlated)
    assert all(e.metadata_json.get("causation_id") == "parent-command" for e in correlated)


def test_agent_cannot_execute_ungranted_mutation_command():
    db = make_session()
    inv = Investigation(title="Running Clubs", slug="running-clubs", status="collecting", confidence=0.91, attributes={})
    db.add(inv); db.commit(); db.refresh(inv)
    command = KernelCommand(
        command_type="CreateHypothesis",
        aggregate_type="investigation",
        aggregate_id=inv.id,
        payload={"title": "Unauthorized", "confidence": 0.5},
        actor_type="agent",
        actor_id="evidence_agent",
    )
    try:
        execute_command(db, command)
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected permission denial")
    assert db.scalar(select(Hypothesis).where(Hypothesis.investigation_id == inv.id)) is None
