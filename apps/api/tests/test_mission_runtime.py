from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.kernel import KernelCommand, execute_command
from app.mission_runtime.engine import get_mission
from app.models.agent import AgentTask
from app.models.investigation import Investigation
from app.models.kernel import KernelCommandLog, KernelEvent
from app.models.mission import InvestigationMission, InvestigationMissionStep


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_investigation(db: Session) -> Investigation:
    investigation = Investigation(
        title="Running Clubs",
        slug="running-clubs-mission",
        status="collecting",
        confidence=0.5,
        attributes={},
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


def test_create_mission_persists_default_plan_and_kernel_lineage():
    db = make_session()
    investigation = make_investigation(db)
    command = KernelCommand(
        command_type="CreateInvestigationMission",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={"objective": "Determine whether running clubs are a durable movement."},
        correlation_id="mission-correlation",
    )

    mission = execute_command(db, command)
    state = get_mission(db, mission.id)

    assert isinstance(mission, InvestigationMission)
    assert mission.status == "pending"
    assert mission.command_id == command.id
    assert mission.correlation_id == "mission-correlation"
    assert len(state["steps"]) == 6
    assert [step.sequence for step in state["steps"]] == [1, 2, 3, 4, 5, 6]
    assert state["steps"][-1].task_type == "SYNTHESIZE_INVESTIGATION"

    event = db.scalar(
        select(KernelEvent).where(
            KernelEvent.aggregate_id == investigation.id,
            KernelEvent.event_type == "InvestigationMissionCreated",
        )
    )
    assert event is not None
    assert event.metadata_json["command_id"] == command.id
    assert event.metadata_json["correlation_id"] == "mission-correlation"


def test_run_mission_executes_steps_as_nested_kernel_commands():
    db = make_session()
    investigation = make_investigation(db)
    create = KernelCommand(
        command_type="CreateInvestigationMission",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={
            "objective": "Audit the investigation with a bounded agent mission.",
            "plan": [
                {
                    "agent_id": "evidence_agent",
                    "task_type": "REVIEW_INVESTIGATION",
                    "inputs": {"test": True},
                }
            ],
        },
        correlation_id="mission-run-correlation",
    )
    mission = execute_command(db, create)

    run = KernelCommand(
        command_type="RunInvestigationMission",
        aggregate_type="mission",
        aggregate_id=mission.id,
        payload={"mission_id": mission.id},
        correlation_id="mission-run-correlation",
        causation_id=create.id,
    )
    state = execute_command(db, run)

    assert state["mission"].status == "completed"
    assert state["mission"].finished_at is not None
    assert len(state["steps"]) == 1
    step = state["steps"][0]
    assert step.status == "completed"
    assert step.task_id is not None
    assert step.command_id is not None
    assert db.get(AgentTask, step.task_id) is not None

    nested_log = db.scalar(
        select(KernelCommandLog).where(KernelCommandLog.command_id == step.command_id)
    )
    assert nested_log is not None
    assert nested_log.command_type == "RunInvestigationAgent"
    assert nested_log.status == "completed"
    assert nested_log.correlation_id == "mission-run-correlation"
    assert nested_log.causation_id == run.id

    event_types = {
        event.event_type
        for event in db.scalars(
            select(KernelEvent).where(KernelEvent.aggregate_id == investigation.id)
        )
    }
    assert {
        "InvestigationMissionStarted",
        "InvestigationMissionStepStarted",
        "InvestigationMissionStepCompleted",
        "InvestigationMissionCompleted",
    }.issubset(event_types)


def test_missing_mission_run_is_audited_as_failed_command():
    db = make_session()
    command = KernelCommand(
        command_type="RunInvestigationMission",
        aggregate_type="mission",
        aggregate_id="missing-mission",
        payload={"mission_id": "missing-mission"},
    )

    try:
        execute_command(db, command)
    except KeyError:
        pass
    else:
        raise AssertionError("Expected missing mission failure")

    log = db.scalar(
        select(KernelCommandLog).where(KernelCommandLog.command_id == command.id)
    )
    assert log is not None
    assert log.status == "failed"
    assert log.error


def test_mission_step_sequence_is_unique_per_mission():
    db = make_session()
    investigation = make_investigation(db)
    mission = InvestigationMission(
        investigation_id=investigation.id,
        objective="Sequence invariant",
        status="pending",
        requested_by="test",
        metadata_json={},
    )
    db.add(mission)
    db.flush()
    db.add_all(
        [
            InvestigationMissionStep(
                mission_id=mission.id,
                investigation_id=investigation.id,
                sequence=1,
                agent_id="evidence_agent",
                task_type="REVIEW_INVESTIGATION",
                status="pending",
                input_json={},
                result_json={},
                finding_ids=[],
            ),
            InvestigationMissionStep(
                mission_id=mission.id,
                investigation_id=investigation.id,
                sequence=1,
                agent_id="quality_agent",
                task_type="REVIEW_INVESTIGATION",
                status="pending",
                input_json={},
                result_json={},
                finding_ids=[],
            ),
        ]
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
    else:
        raise AssertionError("Expected duplicate mission sequence to fail")
