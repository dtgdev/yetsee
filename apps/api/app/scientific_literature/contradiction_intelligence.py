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

    if left_polarity != right_polarity:
        return {
            "status": "direct_contradiction",
            "confidence": 0.95,
            "rationale": "The normalized relationship matches but the explicit assertion polarity differs.",
            "left_polarity": left_polarity,
            "right_polarity": right_polarity,
        }

    return {
        "status": "agreement",
        "confidence": 0.95,
        "rationale": "The normalized relationship and explicit assertion polarity agree.",
        "left_polarity": left_polarity,
        "right_polarity": right_polarity,
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

        direct_count = sum(pair["status"] == "direct_contradiction" for pair in pairwise)
        agreement_count = sum(pair["status"] == "agreement" for pair in pairwise)

        if direct_count:
            overall_status = "direct_contradiction"
        elif agreement_count:
            overall_status = "agreement"
        elif len(source_claims) == 1:
            overall_status = "single_source"
        else:
            overall_status = "unresolved"

        assessments.append({
            "relationship": item["relationship"],
            "source_count": len(source_claims),
            "publication_count": len({source["publication_id"] for source in source_claims}),
            "overall_status": overall_status,
            "agreement_pair_count": agreement_count,
            "direct_contradiction_pair_count": direct_count,
            "pairwise_assessments": pairwise,
            "sources": source_claims,
        })

    contradiction_groups = sum(item["overall_status"] == "direct_contradiction" for item in assessments)
    agreement_groups = sum(item["overall_status"] == "agreement" for item in assessments)

    return {
        "investigation_id": investigation_id,
        "claim_group_count": len(assessments),
        "agreement_group_count": agreement_groups,
        "direct_contradiction_group_count": contradiction_groups,
        "groups": assessments,
        "policy": {
            "derived_contradiction_assessment": True,
            "canonical_evidence": False,
            "does_not_change_evidence_count": True,
            "requires_normalized_relation_match_for_direct_contradiction": True,
            "different_relationships_are_not_assumed_contradictory": True,
            "rejected_claim_candidates_excluded": True,
            "subject_scoped_polarity": True,
            "algorithm": "deterministic-claim-contradiction-v1.1",
        },
    }
