from __future__ import annotations

import re
from itertools import combinations

from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.scientific_literature.synthesis import synthesize_investigation_claims


_NEGATION_RE = re.compile(
    r"\b(no|not|never|neither|without|failed to|did not|does not|was not|were not|is not|are not)\b",
    re.I,
)


_ALTERATION_WORDS = {"amplification", "mutation", "mutations", "deletion", "deletions", "alteration", "alterations"}


def _subject_clause(assertion_text: str, subject_name: str) -> str:
    text = assertion_text or ""
    clauses = [part.strip() for part in re.split(r"[;:]", text) if part.strip()]
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]+", subject_name or "")
        if token.lower() not in _ALTERATION_WORDS
    ]
    if not tokens:
        return text
    for clause in clauses:
        lowered = clause.lower()
        if all(token in lowered for token in tokens):
            return clause
    return text


def claim_polarity(assertion_text: str, subject_name: str = "") -> str:
    relevant_text = _subject_clause(assertion_text, subject_name)
    return "negative" if _NEGATION_RE.search(relevant_text) else "positive"


def _review_state(left: dict, right: dict, semantic_status: str) -> tuple[str, str]:
    both_reviewed = left.get("review_status") == "approve" and right.get("review_status") == "approve"
    if semantic_status == "agreement":
        if both_reviewed:
            return "reviewed_agreement", "Both source claims are human-approved and semantically agree."
        return "provisional_agreement", "The claims agree semantically, but at least one source claim is still pending human review."
    if semantic_status == "direct_contradiction":
        if both_reviewed:
            return "reviewed_contradiction", "Both source claims are human-approved and explicitly contradict one another."
        return "provisional_tension", "Opposing claim polarity is present, but at least one source claim is still pending human review."
    return semantic_status, "Review state does not alter this pair classification."


def classify_claim_pair(left: dict, right: dict) -> dict:
    same_relation = (
        left["relationship"]["subject"]["key"] == right["relationship"]["subject"]["key"]
        and left["relationship"]["predicate"] == right["relationship"]["predicate"]
        and left["relationship"]["object"]["key"] == right["relationship"]["object"]["key"]
    )

    if not same_relation:
        return {
            "status": "not_comparable",
            "confidence": 0.99,
            "rationale": "The normalized subject-predicate-object relationships differ, so YetSee does not treat these claims as direct contradictions.",
        }

    subject_name = left["relationship"]["subject"].get("name", "")
    left_polarity = claim_polarity(left.get("assertion_text", ""), subject_name)
    right_polarity = claim_polarity(right.get("assertion_text", ""), subject_name)

    semantic_status = "direct_contradiction" if left_polarity != right_polarity else "agreement"
    review_aware_status, review_rationale = _review_state(left, right, semantic_status)
    semantic_rationale = (
        "The normalized relationship matches but the explicit assertion polarity differs."
        if semantic_status == "direct_contradiction"
        else "The normalized relationship and explicit assertion polarity agree."
    )
    return {
        "status": review_aware_status,
        "semantic_status": semantic_status,
        "confidence": 0.95,
        "rationale": semantic_rationale,
        "review_rationale": review_rationale,
        "left_polarity": left_polarity,
        "right_polarity": right_polarity,
        "left_review_status": left.get("review_status", "pending"),
        "right_review_status": right.get("review_status", "pending"),
    }


def _source_claim(item: dict, source: dict) -> dict:
    return {
        "relationship": item["relationship"],
        "assertion_text": source["assertion_text"],
        "publication_id": source["publication_id"],
        "pmid": source.get("pmid"),
        "candidate_id": source["candidate_id"],
        "review_status": source["review_status"],
    }


def investigation_contradiction_intelligence(db: Session, investigation_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    syntheses = synthesize_investigation_claims(db, investigation_id)
    assessments: list[dict] = []

    for item in syntheses:
        active_sources = [source for source in item["sources"] if source["review_status"] != "reject"]
        source_claims = [_source_claim(item, source) for source in active_sources]
        if not source_claims:
            continue
        pairwise: list[dict] = []
        for left, right in combinations(source_claims, 2):
            result = classify_claim_pair(left, right)
            pairwise.append({
                "left_candidate_id": left["candidate_id"],
                "right_candidate_id": right["candidate_id"],
                "left_publication_id": left["publication_id"],
                "right_publication_id": right["publication_id"],
                "left_pmid": left.get("pmid"),
                "right_pmid": right.get("pmid"),
                **result,
            })

        reviewed_contradiction_count = sum(pair["status"] == "reviewed_contradiction" for pair in pairwise)
        provisional_tension_count = sum(pair["status"] == "provisional_tension" for pair in pairwise)
        reviewed_agreement_count = sum(pair["status"] == "reviewed_agreement" for pair in pairwise)
        provisional_agreement_count = sum(pair["status"] == "provisional_agreement" for pair in pairwise)

        if reviewed_contradiction_count:
            overall_status = "reviewed_contradiction"
        elif provisional_tension_count:
            overall_status = "provisional_tension"
        elif reviewed_agreement_count:
            overall_status = "reviewed_agreement"
        elif provisional_agreement_count:
            overall_status = "provisional_agreement"
        elif len(source_claims) == 1:
            overall_status = "single_source"
        else:
            overall_status = "unresolved"

        assessments.append({
            "relationship": item["relationship"],
            "source_count": len(source_claims),
            "publication_count": len({source["publication_id"] for source in source_claims}),
            "overall_status": overall_status,
            "reviewed_agreement_pair_count": reviewed_agreement_count,
            "provisional_agreement_pair_count": provisional_agreement_count,
            "reviewed_contradiction_pair_count": reviewed_contradiction_count,
            "provisional_tension_pair_count": provisional_tension_count,
            "agreement_pair_count": reviewed_agreement_count + provisional_agreement_count,
            "direct_contradiction_pair_count": reviewed_contradiction_count + provisional_tension_count,
            "pairwise_assessments": pairwise,
            "sources": source_claims,
        })

    reviewed_contradiction_groups = sum(item["overall_status"] == "reviewed_contradiction" for item in assessments)
    provisional_tension_groups = sum(item["overall_status"] == "provisional_tension" for item in assessments)
    reviewed_agreement_groups = sum(item["overall_status"] == "reviewed_agreement" for item in assessments)
    provisional_agreement_groups = sum(item["overall_status"] == "provisional_agreement" for item in assessments)

    return {
        "investigation_id": investigation_id,
        "claim_group_count": len(assessments),
        "agreement_group_count": reviewed_agreement_groups + provisional_agreement_groups,
        "direct_contradiction_group_count": reviewed_contradiction_groups,
        "reviewed_agreement_group_count": reviewed_agreement_groups,
        "provisional_agreement_group_count": provisional_agreement_groups,
        "reviewed_contradiction_group_count": reviewed_contradiction_groups,
        "provisional_tension_group_count": provisional_tension_groups,
        "groups": assessments,
        "policy": {
            "derived_contradiction_assessment": True,
            "canonical_evidence": False,
            "does_not_change_evidence_count": True,
            "requires_normalized_relation_match_for_direct_contradiction": True,
            "different_relationships_are_not_assumed_contradictory": True,
            "rejected_claim_candidates_excluded": True,
            "subject_scoped_polarity": True,
            "review_aware_classification": True,
            "pending_claims_cannot_create_reviewed_agreement_or_contradiction": True,
            "algorithm": "deterministic-claim-contradiction-v1.2",
        },
    }
