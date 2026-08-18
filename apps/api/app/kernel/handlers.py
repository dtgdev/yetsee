from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent_orchestration.engine import refresh_investigation, run_agent
from app.signal_engine.ingestion import run_connector
from app.signal_engine.matching import match_observations_to_investigations
from app.reasoning_runtime.engine import run_reasoner
import app.reasoning_runtime  # noqa: F401
from app.investigation_runtime.engine import (
    add_hypothesis,
    attach_hypothesis_evidence,
    recalculate_hypothesis_confidence,
    transition_investigation,
)
from app.mission_runtime.engine import create_mission, run_mission
from app.kernel.commands import KernelCommand, execute_command, registry


def _create_hypothesis(db: Session, command: KernelCommand):
    return add_hypothesis(
        db,
        command.aggregate_id or "",
        title=command.payload["title"],
        description=command.payload.get("description"),
        confidence=float(command.payload.get("confidence", 0.5)),
        created_by_type=command.actor_type,
        created_by_id=command.actor_id,
    )


def _link_hypothesis_evidence(db: Session, command: KernelCommand):
    return attach_hypothesis_evidence(
        db,
        command.aggregate_id or "",
        command.payload["hypothesis_id"],
        observation_id=command.payload["observation_id"],
        stance=command.payload["stance"],
        weight=float(command.payload.get("weight", 1.0)),
        rationale=command.payload.get("rationale"),
        author_type=command.actor_type,
        author_id=command.actor_id,
    )


def _recalculate_hypothesis(db: Session, command: KernelCommand):
    return recalculate_hypothesis_confidence(
        db,
        command.aggregate_id or "",
        command.payload["hypothesis_id"],
        reason=command.payload.get("reason", "Kernel confidence recalculation"),
        trigger=command.payload.get("trigger", "kernel_command"),
        author_type=command.actor_type,
        author_id=command.actor_id,
    )


def _transition_investigation(db: Session, command: KernelCommand):
    return transition_investigation(
        db,
        command.aggregate_id or "",
        command.payload["state"],
        reason=command.payload["reason"],
        actor_type=command.actor_type,
        actor_id=command.actor_id,
    )


def _run_investigation_agent(db: Session, command: KernelCommand):
    return run_agent(
        db,
        agent_id=command.payload["agent_id"],
        task_type=command.payload.get("task_type", "AUDIT"),
        target_type="investigation",
        target_id=command.aggregate_id,
        inputs=command.payload.get("inputs") or {},
        requested_by=f"kernel:{command.actor_type}",
    )


def _refresh_investigation(db: Session, command: KernelCommand):
    return refresh_investigation(db, command.aggregate_id or "")


def _create_investigation_mission(db: Session, command: KernelCommand):
    return create_mission(
        db,
        command.aggregate_id or "",
        objective=command.payload["objective"],
        requested_by=f"kernel:{command.actor_type}",
        metadata=command.payload.get("metadata") or {},
        plan=command.payload.get("plan"),
    )


def _run_investigation_mission(db: Session, command: KernelCommand):
    mission_id = command.payload.get("mission_id") or command.aggregate_id
    if not mission_id:
        raise ValueError("mission_id is required")
    return run_mission(db, mission_id)


def _run_connector(db: Session, command: KernelCommand):
    connector_id = command.payload.get("connector_id") or command.aggregate_id
    if not connector_id:
        raise ValueError("connector_id is required")
    run = run_connector(db, connector_id)
    matched = {}
    refreshes = []
    if run.status == "succeeded":
        observation_ids = list((run.metadata_json or {}).get("accepted_observation_ids") or [])
        matched = match_observations_to_investigations(db, observation_ids)
        for investigation_id in sorted(matched):
            refresh_command = KernelCommand(
                command_type="RefreshInvestigation",
                aggregate_type="investigation",
                aggregate_id=investigation_id,
                payload={"trigger": "connector_ingestion", "connector_id": connector_id, "observation_ids": matched[investigation_id]},
                actor_type="system",
                actor_id="connector_runtime",
                correlation_id=command.correlation_id,
                causation_id=command.id,
            )
            refreshes.append(execute_command(db, refresh_command))
        run.metadata_json = {
            **(run.metadata_json or {}),
            "matched_investigations": matched,
            "refreshed_investigations": sorted(matched),
        }
        db.commit()
        db.refresh(run)
    return run


def _run_reasoner(db: Session, command: KernelCommand):
    return run_reasoner(
        db,
        command.aggregate_id or "",
        command.payload.get("reasoner_id", "graph"),
        triggered_by=f"kernel:{command.actor_type}",
    )


HANDLERS = {
    "CreateHypothesis": _create_hypothesis,
    "LinkHypothesisEvidence": _link_hypothesis_evidence,
    "RecalculateHypothesisConfidence": _recalculate_hypothesis,
    "TransitionInvestigation": _transition_investigation,
    "RunInvestigationAgent": _run_investigation_agent,
    "RefreshInvestigation": _refresh_investigation,
    "CreateInvestigationMission": _create_investigation_mission,
    "RunInvestigationMission": _run_investigation_mission,
    "RunConnector": _run_connector,
    "RunReasoner": _run_reasoner,
}

for command_type, handler in HANDLERS.items():
    registry.register(command_type, handler)
