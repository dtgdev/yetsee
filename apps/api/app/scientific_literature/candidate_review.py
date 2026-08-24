from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scientific_literature import ScientificClaimCandidateReview
from app.scientific_literature.candidate_extraction import extract_investigation_claim_candidates
from app.scientific_literature.grounding import ground_claim_relationship

_ALLOWED_DECISIONS = {"approve", "reject"}


def _candidate_for(db: Session, investigation_id: str, candidate_id: str) -> dict:
    for candidate in extract_investigation_claim_candidates(db, investigation_id):
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise KeyError("Scientific claim candidate not found")


def _review_payload(review: ScientificClaimCandidateReview) -> dict:
    return {
        "id": review.id,
        "investigation_id": review.investigation_id,
        "candidate_id": review.candidate_id,
        "decision": review.decision,
        "reviewer": review.reviewer,
        "rationale": review.rationale,
        "candidate_snapshot": review.candidate_snapshot_json,
        "reviewed_claim": review.reviewed_claim_json,
        "scientific_claim_id": review.scientific_claim_id,
        "relationship_id": review.relationship_id,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


def review_candidate(
    db: Session,
    *,
    investigation_id: str,
    candidate_id: str,
    decision: str,
    reviewer: str = "human",
    rationale: str | None = None,
) -> tuple[dict, bool]:
    if decision not in _ALLOWED_DECISIONS:
        raise ValueError("Decision must be approve or reject")

    existing = db.scalar(
        select(ScientificClaimCandidateReview).where(
            ScientificClaimCandidateReview.investigation_id == investigation_id,
            ScientificClaimCandidateReview.candidate_id == candidate_id,
        )
    )
    if existing is not None:
        if existing.decision != decision:
            raise ValueError("Candidate has already been reviewed with a different decision")
        return _review_payload(existing), False

    candidate = _candidate_for(db, investigation_id, candidate_id)
    reviewed_claim: dict = {}
    scientific_claim_id: str | None = None
    relationship_id: str | None = None

    if decision == "approve":
        claim_data = candidate["claim"]
        subject = claim_data["subject"]
        obj = claim_data["object"]
        claim, relationship, _ = ground_claim_relationship(
            db,
            investigation_id=investigation_id,
            passage_id=candidate["provenance"]["passage_id"],
            claim_text=claim_data["assertion_text"],
            subject_kind=subject["kind"],
            subject_name=subject["name"],
            subject_key=subject["key"],
            predicate=claim_data["predicate"],
            object_kind=obj["kind"],
            object_name=obj["name"],
            object_key=obj["key"],
            extraction_method="reviewed_candidate",
            extraction_version=candidate["extraction"]["version"],
        )
        scientific_claim_id = claim.id
        relationship_id = relationship.id
        reviewed_claim = {
            "claim_id": claim.id,
            "relationship_id": relationship.id,
            "claim_text": claim.claim_text,
            "predicate": claim_data["predicate"],
            "canonical_evidence": False,
        }

    review = ScientificClaimCandidateReview(
        investigation_id=investigation_id,
        candidate_id=candidate_id,
        decision=decision,
        reviewer=reviewer,
        rationale=rationale,
        candidate_snapshot_json=candidate,
        reviewed_claim_json=reviewed_claim,
        scientific_claim_id=scientific_claim_id,
        relationship_id=relationship_id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_payload(review), True


def list_candidate_reviews(db: Session, investigation_id: str) -> list[dict]:
    reviews = list(
        db.scalars(
            select(ScientificClaimCandidateReview)
            .where(ScientificClaimCandidateReview.investigation_id == investigation_id)
            .order_by(ScientificClaimCandidateReview.created_at.asc())
        )
    )
    return [_review_payload(review) for review in reviews]
