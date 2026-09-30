from __future__ import annotations

import re
from itertools import combinations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.scientific_literature import ScientificPassage, ScientificPublication
from app.scientific_literature.synthesis import synthesize_investigation_claims


_NEGATION_RE = re.compile(
    r"\b(no|not|never|neither|without|failed to|did not|does not|was not|were not|is not|are not)\b",
    re.I,
)


_ALTERATION_WORDS = {"amplification", "mutation", "mutations", "deletion", "deletions", "alteration", "alterations"}

_TREATMENT_LINE_RULES = (
    ("first_line", re.compile(r"\bfirst[- ]line\b", re.I)),
    ("second_line", re.compile(r"\bsecond[- ]line\b", re.I)),
    ("third_line", re.compile(r"\bthird[- ]line\b", re.I)),
)
_POPULATION_RULES = (
    ("egfr_t790m", re.compile(r"\bEGFR\s*T790M\b", re.I)),
    ("egfr_mutant", re.compile(r"\bEGFR(?:m|[- ]mutant|[- ]mutated)\b", re.I)),
)
_SAMPLING_RULES = (
    ("baseline", re.compile(r"\bbaseline\b", re.I)),
    ("progression", re.compile(r"\bprogression\b", re.I)),
    ("treatment_discontinuation", re.compile(r"\btreatment discontinuation\b", re.I)),
    ("follow_up", re.compile(r"\bfollow[- ]?up\b", re.I)),
)
_ASSAY_RULES = (
    ("next_generation_sequencing", re.compile(r"\bnext[- ]generation sequencing\b|\bNGS\b", re.I)),
    ("circulating_tumor_dna", re.compile(r"\bcirculating[- ]tumou?r DNA\b|\bctDNA\b", re.I)),
    ("plasma", re.compile(r"\bplasma\b", re.I)),
    ("tissue", re.compile(r"\btissue\b", re.I)),
)


def extract_scientific_context(text: str) -> dict:
    clean = text or ""
    treatment_lines = [name for name, pattern in _TREATMENT_LINE_RULES if pattern.search(clean)]
    populations = [name for name, pattern in _POPULATION_RULES if pattern.search(clean)]
    sampling = [name for name, pattern in _SAMPLING_RULES if pattern.search(clean)]
    assays = [name for name, pattern in _ASSAY_RULES if pattern.search(clean)]
    return {
        "treatment_line": treatment_lines,
        "population": populations,
        "sampling_timepoints": sampling,
        "assay_context": assays,
    }


def compare_scientific_context(left: dict, right: dict) -> dict:
    dimensions: list[dict] = []
    divergent_dimensions: list[str] = []
    aligned_dimensions: list[str] = []

    for dimension in ("treatment_line", "population", "sampling_timepoints", "assay_context"):
        left_values = sorted(set(left.get(dimension, [])))
        right_values = sorted(set(right.get(dimension, [])))
        if not left_values and not right_values:
            status = "unknown"
        elif left_values == right_values:
            status = "aligned"
            aligned_dimensions.append(dimension)
        elif set(left_values) & set(right_values):
            status = "partial_overlap"
            divergent_dimensions.append(dimension)
        else:
            status = "different"
            divergent_dimensions.append(dimension)
        dimensions.append({
            "dimension": dimension,
            "status": status,
            "left": left_values,
            "right": right_values,
        })

    observed = [item for item in dimensions if item["status"] != "unknown"]
    if divergent_dimensions:
        overall_status = "contextual_divergence"
        rationale = "The claims address the same normalized relationship, but explicit study context differs on: " + ", ".join(divergent_dimensions) + "."
        confidence = min(0.95, 0.75 + 0.05 * len(divergent_dimensions))
    elif observed:
        overall_status = "context_aligned"
        rationale = "The available explicit context is aligned across the compared publications."
        confidence = min(0.95, 0.7 + 0.04 * len(aligned_dimensions))
    else:
        overall_status = "insufficient_context"
        rationale = "The available text does not expose enough structured context to compare study conditions."
        confidence = 0.5

    return {
        "status": overall_status,
        "confidence": round(confidence, 2),
        "divergent_dimensions": divergent_dimensions,
        "aligned_dimensions": aligned_dimensions,
        "dimensions": dimensions,
        "rationale": rationale,
        "policy": {
            "context_difference_is_not_direct_contradiction": True,
            "missing_context_remains_unknown": True,
        },
    }


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


def _publication_contexts(db: Session, investigation_id: str) -> dict[str, dict]:
    rows = db.execute(
        select(EvidenceLink, ScientificPassage, ScientificPublication)
        .join(ScientificPassage, EvidenceLink.scientific_passage_id == ScientificPassage.id)
        .join(ScientificPublication, ScientificPassage.publication_id == ScientificPublication.id)
        .where(
            EvidenceLink.investigation_id == investigation_id,
            EvidenceLink.scientific_passage_id.is_not(None),
        )
    ).all()
    text_by_publication: dict[str, list[str]] = {}
    for _, passage, publication in rows:
        text_by_publication.setdefault(publication.id, [publication.title])
        text_by_publication[publication.id].append(passage.text)
    return {
        publication_id: extract_scientific_context(" ".join(parts))
        for publication_id, parts in text_by_publication.items()
    }


def _source_claim(item: dict, source: dict, publication_contexts: dict[str, dict]) -> dict:
    return {
        "relationship": item["relationship"],
        "assertion_text": source["assertion_text"],
        "publication_id": source["publication_id"],
        "pmid": source.get("pmid"),
        "candidate_id": source["candidate_id"],
        "review_status": source["review_status"],
        "study_context": publication_contexts.get(source["publication_id"], extract_scientific_context(source["assertion_text"])),
    }


def investigation_contradiction_intelligence(db: Session, investigation_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    syntheses = synthesize_investigation_claims(db, investigation_id)
    publication_contexts = _publication_contexts(db, investigation_id)
    assessments: list[dict] = []

    for item in syntheses:
        active_sources = [source for source in item["sources"] if source["review_status"] != "reject"]
        source_claims = [_source_claim(item, source, publication_contexts) for source in active_sources]
        if not source_claims:
            continue
        pairwise: list[dict] = []
        for left, right in combinations(source_claims, 2):
            result = classify_claim_pair(left, right)
            context_comparison = compare_scientific_context(left.get("study_context", {}), right.get("study_context", {}))
            pairwise.append({
                "left_candidate_id": left["candidate_id"],
                "right_candidate_id": right["candidate_id"],
                "left_publication_id": left["publication_id"],
                "right_publication_id": right["publication_id"],
                "left_pmid": left.get("pmid"),
                "right_pmid": right.get("pmid"),
                "context_comparison": context_comparison,
                **result,
            })

        contextual_divergence_count = sum(pair["context_comparison"]["status"] == "contextual_divergence" for pair in pairwise)
        context_aligned_count = sum(pair["context_comparison"]["status"] == "context_aligned" for pair in pairwise)
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
            "contextual_divergence_pair_count": contextual_divergence_count,
            "context_aligned_pair_count": context_aligned_count,
            "agreement_pair_count": reviewed_agreement_count + provisional_agreement_count,
            "direct_contradiction_pair_count": reviewed_contradiction_count + provisional_tension_count,
            "pairwise_assessments": pairwise,
            "sources": source_claims,
        })

    contextual_divergence_groups = sum(item["contextual_divergence_pair_count"] > 0 for item in assessments)
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
        "contextual_divergence_group_count": contextual_divergence_groups,
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
            "contextual_divergence_is_not_direct_contradiction": True,
            "context_dimensions": ["treatment_line", "population", "sampling_timepoints", "assay_context"],
            "algorithm": "deterministic-claim-contradiction-v1.3",
        },
    }
