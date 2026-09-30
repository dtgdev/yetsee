from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.scientific_literature.contradiction_intelligence import investigation_contradiction_intelligence
from app.scientific_literature.question_evidence_hierarchy import investigation_question_evidence_hierarchy
from app.scientific_literature.study_independence import investigation_study_independence
from app.scientific_literature.study_quality import investigation_study_quality


_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _gap(
    *,
    gap_type: str,
    priority: str,
    title: str,
    rationale: str,
    evidence: dict,
    suggested_next_evidence: list[str],
) -> dict:
    return {
        "gap_type": gap_type,
        "priority": priority,
        "title": title,
        "rationale": rationale,
        "evidence": evidence,
        "suggested_next_evidence": suggested_next_evidence,
    }


def assess_evidence_gaps(
    *,
    quality: dict,
    hierarchy: dict,
    independence: dict,
    contradiction: dict,
) -> list[dict]:
    gaps: list[dict] = []

    study_count = int(quality.get("study_count", 0))
    if study_count == 0:
        gaps.append(_gap(
            gap_type="no_scientific_evidence",
            priority="critical",
            title="No scientific studies are currently linked",
            rationale="The investigation has no scientific publications available for question-specific assessment.",
            evidence={"study_count": 0},
            suggested_next_evidence=["Add directly relevant primary scientific studies before drawing a conclusion."],
        ))
        return gaps

    direct_or_strong = [
        study for study in hierarchy.get("studies", [])
        if study.get("question_fit") in {"direct", "strong"}
    ]
    if not direct_or_strong:
        gaps.append(_gap(
            gap_type="question_fit_gap",
            priority="high",
            title="No directly fitting study for the research question",
            rationale="Available publications may be scientifically useful, but none currently have direct or strong question-specific fit.",
            evidence={
                "question_type": hierarchy.get("question_type"),
                "study_count": hierarchy.get("study_count", 0),
            },
            suggested_next_evidence=["Find a study design that directly addresses the classified research question."],
        ))

    high_or_moderate = int(quality.get("high_or_moderate_quality_count", 0))
    if high_or_moderate == 0:
        gaps.append(_gap(
            gap_type="quality_gap",
            priority="high",
            title="No moderate- or high-quality study signal",
            rationale="All currently available studies have limited or very limited deterministic quality signals.",
            evidence={
                "study_count": study_count,
                "high_or_moderate_quality_count": high_or_moderate,
                "mean_quality_score": quality.get("mean_quality_score"),
            },
            suggested_next_evidence=["Seek stronger primary studies or systematic evidence with clearer design and methods."],
        ))

    independence_status = independence.get("overall_status")
    if study_count == 1:
        gaps.append(_gap(
            gap_type="replication_gap",
            priority="high",
            title="Only one publication contributes scientific evidence",
            rationale="A single publication cannot establish independent replication.",
            evidence={"publication_count": independence.get("publication_count", 0)},
            suggested_next_evidence=["Find an independently conducted study or trial addressing the same relationship."],
        ))
    elif independence_status != "confirmed_independent_trials":
        gaps.append(_gap(
            gap_type="independence_gap",
            priority="high",
            title="Study independence is not fully established",
            rationale="The current publication set does not establish that all compared evidence derives from independent trials or populations.",
            evidence={
                "overall_status": independence_status,
                "confirmed_independent_pair_count": independence.get("confirmed_independent_pair_count", 0),
                "same_trial_pair_count": independence.get("same_trial_pair_count", 0),
                "unresolved_pair_count": independence.get("unresolved_pair_count", 0),
            },
            suggested_next_evidence=["Resolve cohort/trial provenance or add evidence from an explicitly independent trial or population."],
        ))

    if contradiction.get("provisional_tension_group_count", 0):
        gaps.append(_gap(
            gap_type="unresolved_tension",
            priority="high",
            title="Potential contradiction still requires review",
            rationale="At least one claim pair has opposing polarity while one or more source claims remain pending human review.",
            evidence={"provisional_tension_group_count": contradiction.get("provisional_tension_group_count", 0)},
            suggested_next_evidence=["Review the pending source claims and obtain comparable evidence in matched study context."],
        ))

    if contradiction.get("reviewed_contradiction_group_count", 0):
        gaps.append(_gap(
            gap_type="reviewed_contradiction",
            priority="high",
            title="Reviewed evidence contains a direct contradiction",
            rationale="Human-reviewed claims with the same normalized relationship have opposing assertion polarity.",
            evidence={"reviewed_contradiction_group_count": contradiction.get("reviewed_contradiction_group_count", 0)},
            suggested_next_evidence=["Seek independent evidence capable of resolving the contradictory relationship."],
        ))

    provisional_agreement = int(contradiction.get("provisional_agreement_group_count", 0))
    if provisional_agreement:
        gaps.append(_gap(
            gap_type="review_maturity_gap",
            priority="medium",
            title="Agreement remains provisional",
            rationale="Semantically agreeing evidence still includes one or more pending human claim reviews.",
            evidence={"provisional_agreement_group_count": provisional_agreement},
            suggested_next_evidence=["Complete human review of pending source claims before treating agreement as reviewed."],
        ))

    single_source_groups = [
        group for group in contradiction.get("groups", [])
        if group.get("overall_status") == "single_source"
    ]
    if single_source_groups:
        gaps.append(_gap(
            gap_type="claim_replication_gap",
            priority="medium",
            title="One or more scientific claims have only a single source",
            rationale="Some normalized scientific relationships are currently supported by only one publication.",
            evidence={
                "single_source_group_count": len(single_source_groups),
                "relationships": [group.get("relationship") for group in single_source_groups],
            },
            suggested_next_evidence=["Find a second independent publication evaluating each single-source relationship."],
        ))

    contextual_groups = int(contradiction.get("contextual_divergence_group_count", 0))
    if contextual_groups:
        gaps.append(_gap(
            gap_type="context_resolution_gap",
            priority="medium",
            title="Evidence differs across study context",
            rationale="At least one otherwise comparable claim pair differs in population, treatment line, assay, sampling, or another captured study context.",
            evidence={"contextual_divergence_group_count": contextual_groups},
            suggested_next_evidence=["Seek evidence in matched contexts to determine whether the relationship generalizes across the divergent conditions."],
        ))

    gaps.sort(key=lambda item: (_PRIORITY_RANK[item["priority"]], item["gap_type"]))
    return gaps


def investigation_evidence_gap_intelligence(db: Session, investigation_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    quality = investigation_study_quality(db, investigation_id)
    hierarchy = investigation_question_evidence_hierarchy(db, investigation_id)
    independence = investigation_study_independence(db, investigation_id)
    contradiction = investigation_contradiction_intelligence(db, investigation_id)

    gaps = assess_evidence_gaps(
        quality=quality,
        hierarchy=hierarchy,
        independence=independence,
        contradiction=contradiction,
    )

    counts = {priority: sum(gap["priority"] == priority for gap in gaps) for priority in ("critical", "high", "medium", "low")}
    return {
        "investigation_id": investigation_id,
        "gap_count": len(gaps),
        "priority_counts": counts,
        "gaps": gaps,
        "inputs": {
            "study_count": quality.get("study_count", 0),
            "question_type": hierarchy.get("question_type"),
            "independence_status": independence.get("overall_status"),
            "claim_group_count": contradiction.get("claim_group_count", 0),
        },
        "policy": {
            "derived_gap_assessment": True,
            "canonical_evidence": False,
            "does_not_change_evidence_count": True,
            "absence_of_evidence_is_not_evidence_of_absence": True,
            "suggested_next_evidence_is_investigation_guidance": True,
            "algorithm": "deterministic-evidence-gap-intelligence-v1",
        },
    }
