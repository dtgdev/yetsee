from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.discovery_engine.engine import promote_candidate
from app.kernel import KernelCommand, execute_command
from app.models.discovery import DiscoveryCandidate
from app.models.kernel import KernelCommandLog, KernelEvent
from app.models.reasoning import ReasoningResult, ReasoningRun
from app.signal_engine.ingestion import run_connector
from app.workflow_engine.engine import run_workflow


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_graph_reasoner_runs_through_kernel_and_is_replayable():
    db = make_session()
    run_connector(db, "demo")
    run_workflow(db, "intelligence-refresh", hours=720)
    candidate = db.scalar(select(DiscoveryCandidate).where(DiscoveryCandidate.canonical_key == "running clubs"))
    assert candidate is not None
    investigation = promote_candidate(db, candidate.id, allow_override=True, override_reason="reasoning test")

    result = execute_command(db, KernelCommand(
        command_type="RunReasoner",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={"reasoner_id": "graph"},
    ))

    assert isinstance(result, ReasoningResult)
    assert result.reasoner_id == "graph"
    assert 0.0 <= result.confidence <= 1.0
    assert result.explanation
    assert isinstance(result.metrics, dict)

    reasoning_run = db.get(ReasoningRun, result.run_id)
    assert reasoning_run is not None
    assert reasoning_run.status == "completed"
    assert reasoning_run.command_id is not None

    command = db.scalar(select(KernelCommandLog).where(KernelCommandLog.command_id == reasoning_run.command_id))
    assert command is not None
    assert command.command_type == "RunReasoner"
    assert command.status == "completed"

    event_types = {row.event_type for row in db.scalars(select(KernelEvent).where(KernelEvent.aggregate_id == investigation.id))}
    assert "ReasoningStarted" in event_types
    assert "ReasoningCompleted" in event_types
