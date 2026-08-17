from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kernel.commands import current_command_context
from app.kernel.events import publish_event
from app.kernel.investigations import commit_investigation
from app.models.investigation import Investigation
from app.models.kernel import InvestigationRevision
from app.models.reasoning import ReasoningResult, ReasoningRun
from app.reasoning_runtime.registry import registry


def run_reasoner(db: Session, investigation_id: str, reasoner_id: str, *, triggered_by: str = "human") -> ReasoningResult:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError(investigation_id)
    reasoner = registry.get(reasoner_id)
    manifest = reasoner.manifest()
    latest_revision = db.scalar(select(InvestigationRevision).where(InvestigationRevision.investigation_id == investigation_id).order_by(InvestigationRevision.revision_number.desc()))
    context = current_command_context()
    run = ReasoningRun(
        investigation_id=investigation_id,
        reasoner_id=manifest.id,
        reasoner_version=manifest.version,
        status="running",
        triggered_by=triggered_by,
        command_id=context.command_id if context else None,
        correlation_id=context.correlation_id if context else None,
        input_revision_id=latest_revision.id if latest_revision else None,
        input_snapshot={"revision_number": latest_revision.revision_number if latest_revision else None},
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    publish_event(db, event_type="ReasoningStarted", aggregate_type="investigation", aggregate_id=investigation_id, payload={"run_id": run.id, "reasoner_id": manifest.id, "version": manifest.version})
    try:
        output = reasoner.execute(db, investigation_id)
        result = ReasoningResult(
            run_id=run.id,
            investigation_id=investigation_id,
            reasoner_id=manifest.id,
            conclusion=output.conclusion,
            confidence=max(0.0, min(1.0, output.confidence)),
            support_level=output.support_level,
            supporting_factors=output.supporting_factors,
            contradicting_factors=output.contradicting_factors,
            assumptions=output.assumptions,
            limitations=output.limitations,
            recommended_evidence=output.recommended_evidence,
            evidence_ids=output.evidence_ids,
            metrics=output.metrics,
            explanation=output.explanation,
        )
        db.add(result)
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.flush()
        publish_event(db, event_type="ReasoningCompleted", aggregate_type="investigation", aggregate_id=investigation_id, payload={"run_id": run.id, "result_id": result.id, "reasoner_id": manifest.id, "confidence": result.confidence, "support_level": result.support_level})
        commit_investigation(db, investigation, message=f"{manifest.name} completed with {result.confidence:.3f} confidence", change_type="reasoning_completed", author_type="reasoner", author_id=manifest.id)
        db.commit()
        db.refresh(result)
        return result
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:4000]
        run.finished_at = datetime.now(timezone.utc)
        publish_event(db, event_type="ReasoningFailed", aggregate_type="investigation", aggregate_id=investigation_id, payload={"run_id": run.id, "reasoner_id": manifest.id, "error": str(exc)[:1000]})
        db.commit()
        raise


def list_runs(db: Session, investigation_id: str | None = None) -> list[ReasoningRun]:
    statement = select(ReasoningRun)
    if investigation_id:
        statement = statement.where(ReasoningRun.investigation_id == investigation_id)
    return list(db.scalars(statement.order_by(ReasoningRun.started_at.desc())))


def list_results(db: Session, investigation_id: str | None = None) -> list[ReasoningResult]:
    statement = select(ReasoningResult)
    if investigation_id:
        statement = statement.where(ReasoningResult.investigation_id == investigation_id)
    return list(db.scalars(statement.order_by(ReasoningResult.created_at.desc())))
