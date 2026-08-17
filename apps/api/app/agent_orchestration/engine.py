from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_orchestration.contracts import AgentTaskContext
from app.agent_orchestration.registry import registry
from app.models.agent import AgentFinding, AgentRun, AgentTask
from app.models.hypothesis import Hypothesis
from app.kernel.events import publish_event
from app.investigation_runtime.engine import recalculate_hypothesis_confidence


DEFAULT_CONSTRAINTS = {
    "may_mutate_observations": False,
    "may_delete_evidence": False,
    "may_silently_merge_entities": False,
    "may_create_findings": True,
}


def create_task(db: Session, *, agent_id: str, task_type: str, target_type: str | None = None,
                target_id: str | None = None, inputs: dict | None = None,
                constraints: dict | None = None, requested_by: str = "system",
                priority: int = 50) -> AgentTask:
    registry.get(agent_id)
    task = AgentTask(
        agent_id=agent_id,
        task_type=task_type,
        target_type=target_type,
        target_id=target_id,
        requested_by=requested_by,
        priority=priority,
        input_json=inputs or {},
        constraints={**DEFAULT_CONSTRAINTS, **(constraints or {})},
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def execute_task(db: Session, task_id: str) -> AgentTask:
    task = db.get(AgentTask, task_id)
    if task is None:
        raise KeyError(task_id)
    agent = registry.get(task.agent_id)
    manifest = agent.manifest()
    forbidden = {"write:observations", "delete:evidence", "silent:entity_merge"}
    if forbidden.intersection(manifest.permissions):
        raise PermissionError(f"Agent {manifest.id} requests forbidden canonical-data permissions")
    now = datetime.now(timezone.utc)
    task.status = "running"
    task.started_at = now
    run = AgentRun(
        task_id=task.id,
        agent_id=manifest.id,
        agent_version=manifest.version,
        status="running",
        started_at=now,
        input_json={"task_type": task.task_type, "target_type": task.target_type, "target_id": task.target_id, **task.input_json},
    )
    db.add(run)
    db.flush()
    if task.target_type == "investigation" and task.target_id:
        publish_event(
            db, event_type="AgentRunStarted", aggregate_type="investigation", aggregate_id=task.target_id,
            payload={"task_id": task.id, "run_id": run.id, "agent_id": manifest.id, "task_type": task.task_type},
            metadata={"actor_type": "agent", "actor_id": manifest.id},
        )
    try:
        context = AgentTaskContext(
            task_id=task.id,
            task_type=task.task_type,
            target_type=task.target_type,
            target_id=task.target_id,
            inputs=task.input_json,
            constraints=task.constraints,
        )
        result = agent.execute(db, context)
        finding_count = 0
        for draft in result.findings:
            finding = AgentFinding(
                task_id=task.id,
                agent_id=manifest.id,
                target_type=task.target_type,
                target_id=task.target_id,
                category=draft.category,
                severity=draft.severity,
                stance=draft.stance,
                confidence=max(0.0, min(1.0, draft.confidence)),
                title=draft.title,
                detail=draft.detail,
                evidence_ids=draft.evidence_ids,
                metadata_json=draft.metadata,
            )
            db.add(finding)
            db.flush()
            finding_count += 1
            if task.target_type == "investigation" and task.target_id:
                publish_event(
                    db, event_type="AgentFindingCreated", aggregate_type="investigation", aggregate_id=task.target_id,
                    payload={"finding_id": finding.id, "agent_id": manifest.id, "category": draft.category, "severity": draft.severity, "title": draft.title},
                    metadata={"actor_type": "agent", "actor_id": manifest.id},
                )
        task.status = "completed" if result.status == "completed" else result.status
        task.result_json = {
            "summary": result.summary,
            "recommendation": result.recommendation,
            "confidence": result.confidence,
            **result.output,
        }
        run.status = task.status
        run.output_json = task.result_json
        run.permissions_used = result.permissions_used
        if task.target_type == "investigation" and task.target_id:
            publish_event(
                db, event_type="AgentRunCompleted", aggregate_type="investigation", aggregate_id=task.target_id,
                payload={"task_id": task.id, "run_id": run.id, "agent_id": manifest.id, "status": task.status, "finding_count": finding_count, "recommendation": result.recommendation},
                metadata={"actor_type": "agent", "actor_id": manifest.id},
            )
    except Exception as exc:
        task.status = "failed"
        task.error = str(exc)[:4000]
        run.status = "failed"
        run.error = task.error
    finished = datetime.now(timezone.utc)
    task.finished_at = finished
    run.finished_at = finished
    db.commit()
    db.refresh(task)
    return task


def run_agent(db: Session, *, agent_id: str, task_type: str, target_type: str | None = None,
              target_id: str | None = None, inputs: dict | None = None,
              requested_by: str = "api") -> AgentTask:
    task = create_task(db, agent_id=agent_id, task_type=task_type, target_type=target_type,
                       target_id=target_id, inputs=inputs, requested_by=requested_by)
    return execute_task(db, task.id)


def run_investigation_team(db: Session, investigation_id: str) -> dict:
    # The coordinator does not delegate by free-form conversation. It emits typed, audited tasks.
    ordered = ["evidence_agent", "evidence_critic", "graph_analyst", "opportunity_analyst", "quality_agent", "investigation_agent"]
    tasks = []
    for agent_id in ordered:
        task = run_agent(
            db,
            agent_id=agent_id,
            task_type="REVIEW_INVESTIGATION" if agent_id != "investigation_agent" else "SYNTHESIZE_INVESTIGATION",
            target_type="investigation",
            target_id=investigation_id,
            inputs={"team_run": True},
            requested_by="investigation_team",
        )
        tasks.append(task)
    findings_count = db.scalar(select(func.count()).select_from(AgentFinding).where(AgentFinding.target_id == investigation_id)) or 0
    return {"investigation_id": investigation_id, "tasks": tasks, "findings": findings_count}


def refresh_investigation(db: Session, investigation_id: str) -> dict:
    """Run the deterministic evidence review + confidence refresh loop.

    Agents may create audited findings but never rewrite observations. Confidence is
    recalculated only from already-linked directional evidence.
    """
    task = run_agent(
        db,
        agent_id="evidence_agent",
        task_type="REFRESH_INVESTIGATION_EVIDENCE",
        target_type="investigation",
        target_id=investigation_id,
        inputs={"refresh": True},
        requested_by="investigation_refresh",
    )
    hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.investigation_id == investigation_id)))
    confidence_updates = []
    for hypothesis in hypotheses:
        result = recalculate_hypothesis_confidence(
            db, investigation_id, hypothesis.id,
            reason="Investigation Evidence Agent refresh",
            trigger="evidence_agent_refresh",
            author_type="agent",
            author_id="evidence_agent",
            commit=False,
        )
        history = result["history"]
        confidence_updates.append({
            "hypothesis_id": hypothesis.id,
            "old_confidence": history.old_confidence,
            "new_confidence": history.new_confidence,
            "changed": history.old_confidence != history.new_confidence,
        })
    publish_event(
        db, event_type="InvestigationRefreshed", aggregate_type="investigation", aggregate_id=investigation_id,
        payload={"agent_task_id": task.id, "hypotheses": confidence_updates},
        metadata={"actor_type": "agent", "actor_id": "evidence_agent"},
    )
    db.commit()
    return {
        "investigation_id": investigation_id,
        "agent_task": task,
        "confidence_updates": confidence_updates,
    }
