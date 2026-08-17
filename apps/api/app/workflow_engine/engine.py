from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.discovery_engine.engine import run_discovery
from app.feature_engine.engine import recompute_features
from app.kernel.events import publish_event
from app.knowledge_graph.engine import rebuild_graph
from app.models.kernel import WorkflowRun
from app.semantic_engine.engine import recompute_semantics


WORKFLOWS = {
    "intelligence-refresh": ("features", "semantics", "graph", "discovery"),
}


def run_workflow(db: Session, workflow_id: str, *, hours: int = 720) -> WorkflowRun:
    if workflow_id not in WORKFLOWS:
        raise KeyError(workflow_id)

    run = WorkflowRun(workflow_id=workflow_id, status="running", steps=[])
    db.add(run)
    db.flush()
    publish_event(
        db,
        event_type="WorkflowStarted",
        aggregate_type="workflow",
        aggregate_id=run.id,
        payload={"workflow_id": workflow_id, "hours": hours},
    )

    step_functions: dict[str, Callable[[], object]] = {
        "features": lambda: recompute_features(db, hours=hours),
        "semantics": lambda: recompute_semantics(db, hours=hours),
        "graph": lambda: rebuild_graph(db, hours=hours),
        "discovery": lambda: run_discovery(db, hours=hours),
    }

    steps: list[dict] = []
    try:
        for name in WORKFLOWS[workflow_id]:
            started = datetime.now(timezone.utc)
            result = step_functions[name]()
            finished = datetime.now(timezone.utc)
            steps.append(
                {
                    "name": name,
                    "status": "succeeded",
                    "started_at": started.isoformat(),
                    "finished_at": finished.isoformat(),
                    "result_type": type(result).__name__,
                }
            )
            publish_event(
                db,
                event_type="WorkflowStepCompleted",
                aggregate_type="workflow",
                aggregate_id=run.id,
                payload={"step": name},
            )
        run.status = "succeeded"
    except Exception as exc:
        steps.append({"name": name, "status": "failed", "error": str(exc)})
        run.status = "failed"
        run.error = str(exc)
        publish_event(
            db,
            event_type="WorkflowFailed",
            aggregate_type="workflow",
            aggregate_id=run.id,
            payload={"step": name, "error": str(exc)},
        )
        db.commit()
        raise
    finally:
        run.steps = steps
        run.finished_at = datetime.now(timezone.utc)

    publish_event(
        db,
        event_type="WorkflowCompleted",
        aggregate_type="workflow",
        aggregate_id=run.id,
        payload={"workflow_id": workflow_id, "steps": len(steps)},
    )
    db.commit()
    db.refresh(run)
    return run
