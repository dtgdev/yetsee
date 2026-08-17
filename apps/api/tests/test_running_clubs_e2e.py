from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.discovery_engine.engine import promote_candidate
from app.investigation_runtime.engine import investigation_workspace
from app.kernel import KernelCommand, execute_command
from app.models.discovery import DiscoveryCandidate
from app.models.kernel import KernelCommandLog, KernelEvent
from app.models.observation import Observation
from app.signal_engine.ingestion import run_connector
from app.workflow_engine.engine import run_workflow


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_running_clubs_full_workflow_is_replayable_and_audited():
    db = make_session()

    connector_run = run_connector(db, "demo")
    assert connector_run.status == "succeeded"
    assert connector_run.accepted_count >= 4

    workflow = run_workflow(db, "intelligence-refresh", hours=720)
    assert workflow.status == "succeeded"

    candidate = db.scalar(select(DiscoveryCandidate).where(DiscoveryCandidate.canonical_key == "running clubs"))
    assert candidate is not None
    investigation = promote_candidate(
        db,
        candidate.id,
        allow_override=True,
        override_reason="Golden Running Clubs workflow",
    )

    hypothesis = execute_command(
        db,
        KernelCommand(
            command_type="CreateHypothesis",
            aggregate_type="investigation",
            aggregate_id=investigation.id,
            payload={
                "title": "Running clubs are becoming a broader lifestyle movement",
                "description": "Community-led running expands beyond fitness.",
                "confidence": 0.62,
            },
        ),
    )

    observation = db.scalar(
        select(Observation).where(
            Observation.topic == "running clubs",
            Observation.metric == "community_velocity",
        )
    )
    assert observation is not None

    execute_command(
        db,
        KernelCommand(
            command_type="LinkHypothesisEvidence",
            aggregate_type="investigation",
            aggregate_id=investigation.id,
            payload={
                "hypothesis_id": hypothesis.id,
                "observation_id": observation.id,
                "stance": "supporting",
                "weight": 1.0,
                "rationale": "Golden workflow supporting evidence",
            },
        ),
    )

    agent_task = execute_command(
        db,
        KernelCommand(
            command_type="RunInvestigationAgent",
            aggregate_type="investigation",
            aggregate_id=investigation.id,
            payload={"agent_id": "evidence_agent", "task_type": "AUDIT_INVESTIGATION_EVIDENCE"},
        ),
    )
    assert agent_task.status == "completed"

    workspace = investigation_workspace(db, investigation.id)
    assert workspace["hypotheses"][0].confidence > 0.62
    assert len(workspace["observations"]) >= 1
    assert len(workspace["agent_findings"]) >= 1
    assert len(workspace["timeline"]) >= 1
    assert len(workspace["revisions"]) >= 2

    commands = list(db.scalars(select(KernelCommandLog).where(KernelCommandLog.aggregate_id == investigation.id)))
    command_types = {item.command_type for item in commands}
    assert {"CreateHypothesis", "LinkHypothesisEvidence", "RunInvestigationAgent"}.issubset(command_types)
    assert all(item.status == "completed" for item in commands)

    events = list(db.scalars(select(KernelEvent).where(KernelEvent.aggregate_id == investigation.id)))
    event_types = {event.event_type for event in events}
    assert "HypothesisAdded" in event_types
    assert "EvidenceLinked" in event_types
    assert "AgentRunCompleted" in event_types
