from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.kernel.events import publish_event
from app.models.hypothesis import Hypothesis, HypothesisEvidenceLink
from app.models.investigation import Investigation
from app.models.kernel import InvestigationRevision


def snapshot(db: Session, investigation: Investigation) -> dict:
    hypotheses = list(db.scalars(
        select(Hypothesis)
        .where(Hypothesis.investigation_id == investigation.id)
        .order_by(Hypothesis.created_at.asc())
    ))
    hypothesis_ids = [item.id for item in hypotheses]
    evidence_links = []
    if hypothesis_ids:
        evidence_links = list(db.scalars(
            select(HypothesisEvidenceLink)
            .where(HypothesisEvidenceLink.hypothesis_id.in_(hypothesis_ids))
            .order_by(HypothesisEvidenceLink.created_at.asc())
        ))
    return {
        "id": investigation.id,
        "title": investigation.title,
        "slug": investigation.slug,
        "status": investigation.status,
        "confidence": investigation.confidence,
        "summary": investigation.summary,
        "hypothesis": investigation.hypothesis,
        "counter_thesis": investigation.counter_thesis,
        "attributes": investigation.attributes,
        "hypotheses": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "status": item.status,
                "prior_confidence": item.prior_confidence,
                "confidence": item.confidence,
            }
            for item in hypotheses
        ],
        "hypothesis_evidence": [
            {
                "id": item.id,
                "hypothesis_id": item.hypothesis_id,
                "observation_id": item.observation_id,
                "stance": item.stance,
                "weight": item.weight,
                "rationale": item.rationale,
            }
            for item in evidence_links
        ],
    }


def commit_investigation(
    db: Session,
    investigation: Investigation,
    *,
    message: str,
    change_type: str = "snapshot",
    author_type: str = "system",
    author_id: str | None = None,
) -> InvestigationRevision:
    current = db.scalar(
        select(func.max(InvestigationRevision.revision_number)).where(
            InvestigationRevision.investigation_id == investigation.id
        )
    )
    revision = InvestigationRevision(
        investigation_id=investigation.id,
        revision_number=int(current or 0) + 1,
        change_type=change_type,
        message=message,
        snapshot=snapshot(db, investigation),
        author_type=author_type,
        author_id=author_id,
    )
    db.add(revision)
    db.flush()
    publish_event(
        db,
        event_type="InvestigationCommitted",
        aggregate_type="investigation",
        aggregate_id=investigation.id,
        payload={"revision_id": revision.id, "revision_number": revision.revision_number, "message": message},
    )
    return revision


def history(db: Session, investigation_id: str) -> list[InvestigationRevision]:
    return list(
        db.scalars(
            select(InvestigationRevision)
            .where(InvestigationRevision.investigation_id == investigation_id)
            .order_by(InvestigationRevision.revision_number.desc())
        )
    )
