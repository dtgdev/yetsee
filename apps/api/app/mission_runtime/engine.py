from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_orchestration.engine import run_agent
from app.kernel.commands import current_command_context
from app.kernel.events import publish_event
from app.models.agent import AgentFinding
from app.models.investigation import Investigation
from app.models.mission import InvestigationMission, InvestigationMissionStep


DEFAULT_MISSION_PLAN = (
    ("evidence_agent", "REVIEW_INVESTIGATION"),
    ("evidence_critic", "REVIEW_INVESTIGATION"),
    ("graph_analyst", "REVIEW_INVESTIGATION"),
    ("opportunity_analyst", "REVIEW_INVESTIGATION"),
    ("quality_agent", "REVIEW_INVESTIGATION"),
    ("investigation_agent", "SYNTHESIZE_INVESTIGATION"),
)

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _command_lineage() -> tuple[str | None, str | None]:
    context = current_command_context()
    if context is None:
        return None, None
    return context.command_id, context.correlation_id


def create_mission(
    db: Session,
    investigation_id: str,
    *,
    objective: str,
    requested_by: str = "human",
    metadata: dict[str, Any] | None = None,
    plan: list[dict[str, Any]] | None = None,
) -> InvestigationMission:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError(investigation_id)
    objective = objective.strip()
    if not objective:
        raise ValueError("Mission objective is required")

    command_id, correlation_id = _command_lineage()
    mission = InvestigationMission(
        investigation_id=investigation_id,
        objective=objective,
        status="pending",
        requested_by=requested_by,
        command_id=command_id,
        correlation_id=correlation_id,
        metadata_json=metadata or {},
    )
    db.add(mission)
    db.flush()

    mission_plan = plan or [
        {"agent_id": agent_id, "task_type": task_type, "inputs": {}}
        for agent_id, task_type in DEFAULT_MISSION_PLAN
    ]
    if not mission_plan:
        raise ValueError("Mission plan must contain at least one step")

    for sequence, spec in enumerate(mission_plan, start=1):
        agent_id = str(spec.get("agent_id") or "").strip()
        task_type = str(spec.get("task_type") or "").strip()
        if not agent_id or not task_type:
            raise ValueError("Every mission step requires agent_id and task_type")
        db.add(
            InvestigationMissionStep(
                mission_id=mission.id,
                investigation_id=investigation_id,
                sequence=sequence,
                agent_id=agent_id,
                task_type=task_type,
                status="pending",
                input_json=dict(spec.get("inputs") or {}),
            )
        )

    publish_event(
        db,
        event_type="InvestigationMissionCreated",
        aggregate_type="investigation",
        aggregate_id=investigation_id,
        payload={
            "mission_id": mission.id,
            "objective": objective,
            "step_count": len(mission_plan),
        },
    )
    db.commit()
    db.refresh(mission)
    return mission


def get_mission(db: Session, mission_id: str) -> dict[str, Any]:
    mission = db.get(InvestigationMission, mission_id)
    if mission is None:
        raise KeyError(mission_id)
    steps = list(
        db.scalars(
            select(InvestigationMissionStep)
            .where(InvestigationMissionStep.mission_id == mission_id)
            .order_by(InvestigationMissionStep.sequence.asc())
        )
    )
    return {"mission": mission, "steps": steps}


def list_missions(db: Session, investigation_id: str, *, limit: int = 50) -> list[InvestigationMission]:
    return list(
        db.scalars(
            select(InvestigationMission)
            .where(InvestigationMission.investigation_id == investigation_id)
            .order_by(InvestigationMission.created_at.desc())
            .limit(limit)
        )
    )


def run_mission(db: Session, mission_id: str) -> dict[str, Any]:
    mission = db.get(InvestigationMission, mission_id)
    if mission is None:
        raise KeyError(mission_id)
    if mission.status == "running":
        raise ValueError("Mission is already running")
    if mission.status == "completed":
        return get_mission(db, mission_id)
    if mission.status in {"cancelled"}:
        raise ValueError(f"Mission cannot run from status {mission.status}")

    steps = list(
        db.scalars(
            select(InvestigationMissionStep)
            .where(InvestigationMissionStep.mission_id == mission_id)
            .order_by(InvestigationMissionStep.sequence.asc())
        )
    )
    if not steps:
        raise ValueError("Mission has no steps")

    command_id, correlation_id = _command_lineage()
    if command_id:
        mission.command_id = command_id
    if correlation_id:
        mission.correlation_id = correlation_id
    mission.status = "running"
    mission.error = None
    mission.started_at = mission.started_at or _utcnow()
    mission.finished_at = None
    publish_event(
        db,
        event_type="InvestigationMissionStarted",
        aggregate_type="investigation",
        aggregate_id=mission.investigation_id,
        payload={"mission_id": mission.id, "objective": mission.objective},
    )
    db.commit()

    for step in steps:
        if step.status == "completed":
            continue
        step.command_id = command_id
        step.status = "running"
        step.error = None
        step.started_at = _utcnow()
        step.finished_at = None
        publish_event(
            db,
            event_type="InvestigationMissionStepStarted",
            aggregate_type="investigation",
            aggregate_id=mission.investigation_id,
            payload={
                "mission_id": mission.id,
                "step_id": step.id,
                "sequence": step.sequence,
                "agent_id": step.agent_id,
                "task_type": step.task_type,
            },
        )
        db.commit()

        try:
            task = run_agent(
                db,
                agent_id=step.agent_id,
                task_type=step.task_type,
                target_type="investigation",
                target_id=mission.investigation_id,
                inputs={
                    **(step.input_json or {}),
                    "mission_id": mission.id,
                    "mission_step_id": step.id,
                    "mission_objective": mission.objective,
                    "mission_sequence": step.sequence,
                },
                requested_by=f"mission:{mission.id}",
            )
            step = db.get(InvestigationMissionStep, step.id)
            step.task_id = task.id
            step.status = task.status
            step.result_json = dict(task.result_json or {})
            step.error = task.error
            step.finished_at = task.finished_at or _utcnow()
            step.finding_ids = list(
                db.scalars(
                    select(AgentFinding.id)
                    .where(AgentFinding.task_id == task.id)
                    .order_by(AgentFinding.created_at.asc())
                )
            )
            publish_event(
                db,
                event_type="InvestigationMissionStepCompleted" if task.status == "completed" else "InvestigationMissionStepFailed",
                aggregate_type="investigation",
                aggregate_id=mission.investigation_id,
                payload={
                    "mission_id": mission.id,
                    "step_id": step.id,
                    "sequence": step.sequence,
                    "agent_id": step.agent_id,
                    "task_id": task.id,
                    "status": task.status,
                    "finding_ids": step.finding_ids,
                },
            )
            db.commit()
            if task.status != "completed":
                raise RuntimeError(task.error or f"Agent task ended with status {task.status}")
        except Exception as exc:
            db.rollback()
            mission = db.get(InvestigationMission, mission_id)
            step = db.get(InvestigationMissionStep, step.id)
            if step is not None and step.status != "completed":
                step.status = "failed"
                step.error = str(exc)[:4000]
                step.finished_at = _utcnow()
            mission.status = "failed"
            mission.error = str(exc)[:4000]
            mission.finished_at = _utcnow()
            publish_event(
                db,
                event_type="InvestigationMissionFailed",
                aggregate_type="investigation",
                aggregate_id=mission.investigation_id,
                payload={
                    "mission_id": mission.id,
                    "step_id": step.id if step is not None else None,
                    "error": mission.error,
                },
            )
            db.commit()
            return get_mission(db, mission_id)

    mission = db.get(InvestigationMission, mission_id)
    mission.status = "completed"
    mission.error = None
    mission.finished_at = _utcnow()
    publish_event(
        db,
        event_type="InvestigationMissionCompleted",
        aggregate_type="investigation",
        aggregate_id=mission.investigation_id,
        payload={"mission_id": mission.id, "objective": mission.objective, "step_count": len(steps)},
    )
    db.commit()
    return get_mission(db, mission_id)
