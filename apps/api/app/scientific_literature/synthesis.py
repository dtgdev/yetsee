from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scientific_literature import ScientificClaimCandidateReview
from app.scientific_literature.candidate_extraction import extract_investigation_claim_candidates


def _relationship_key(candidate: dict) -> tuple[str, str, str]:
    claim = candidate["claim"]
    return (
        claim["subject"]["key"],
        claim["predicate"],
        claim["object"]["key"],
    )


def _strength(*, independent_publications: int, approved: int, rejected: int) -> str:
    if approved >= 2 and independent_publications >= 2 and rejected == 0:
        return "reviewed_multi_study"
    if independent_publications >= 2 and rejected == 0:
        return "multi_study_candidate"
    if approved >= 1 and rejected == 0:
        return "reviewed_single_study"
    if approved and rejected:
        return "review_disagreement"
    if rejected and not approved:
        return "rejected"
    return "single_study_candidate"


def synthesize_investigation_claims(db: Session, investigation_id: str) -> list[dict]:
    candidates = extract_investigation_claim_candidates(db, investigation_id)
    reviews = list(
        db.scalars(
            select(ScientificClaimCandidateReview).where(
                ScientificClaimCandidateReview.investigation_id == investigation_id
            )
        )
    )
    reviews_by_candidate = {review.candidate_id: review for review in reviews}

    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for candidate in candidates:
        grouped[_relationship_key(candidate)].append(candidate)

    syntheses: list[dict] = []
    for key, group in grouped.items():
        first = group[0]
        claim = first["claim"]
        publication_ids = {item["provenance"]["publication_id"] for item in group}
        pmids = sorted({item["provenance"].get("pmid") for item in group if item["provenance"].get("pmid")})
        dois = sorted({item["provenance"].get("doi") for item in group if item["provenance"].get("doi")})
        approved_reviews = [reviews_by_candidate[item["candidate_id"]] for item in group if item["candidate_id"] in reviews_by_candidate and reviews_by_candidate[item["candidate_id"]].decision == "approve"]
        rejected_reviews = [reviews_by_candidate[item["candidate_id"]] for item in group if item["candidate_id"] in reviews_by_candidate and reviews_by_candidate[item["candidate_id"]].decision == "reject"]
        pending_count = sum(1 for item in group if item["candidate_id"] not in reviews_by_candidate)

        sources = []
        for item in group:
            review = reviews_by_candidate.get(item["candidate_id"])
            sources.append({
                "candidate_id": item["candidate_id"],
                "review_status": review.decision if review else "pending",
                "scientific_claim_id": review.scientific_claim_id if review else None,
                "relationship_id": review.relationship_id if review else None,
                "assertion_text": item["claim"]["assertion_text"],
                "extraction_confidence": item["extraction"]["confidence"],
                "passage_id": item["provenance"]["passage_id"],
                "publication_id": item["provenance"]["publication_id"],
                "pmid": item["provenance"].get("pmid"),
                "doi": item["provenance"].get("doi"),
                "source_url": item["provenance"].get("source_url"),
                "locator": item["provenance"].get("locator"),
            })

        independent_publication_count = len(publication_ids)
        syntheses.append({
            "relationship": {
                "subject": claim["subject"],
                "predicate": claim["predicate"],
                "object": claim["object"],
            },
            "candidate_count": len(group),
            "independent_publication_count": independent_publication_count,
            "approved_count": len(approved_reviews),
            "rejected_count": len(rejected_reviews),
            "pending_count": pending_count,
            "review_complete": pending_count == 0,
            "strength": _strength(
                independent_publications=independent_publication_count,
                approved=len(approved_reviews),
                rejected=len(rejected_reviews),
            ),
            "pmids": pmids,
            "dois": dois,
            "sources": sources,
            "policy": {
                "derived_synthesis": True,
                "canonical_evidence": False,
                "does_not_change_evidence_count": True,
            },
        })

    return sorted(
        syntheses,
        key=lambda item: (
            -item["independent_publication_count"],
            -item["approved_count"],
            item["relationship"]["subject"]["name"],
        ),
    )
