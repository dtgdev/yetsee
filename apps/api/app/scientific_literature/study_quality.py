from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.scientific_literature import ScientificPassage, ScientificPublication


@dataclass(frozen=True)
class DesignSignal:
    study_design: str
    evidence_level: str
    base_score: int
    rationale: str


_DESIGN_RULES: tuple[tuple[re.Pattern[str], DesignSignal], ...] = (
    (re.compile(r"\b(systematic review|meta-analysis|meta analysis)\b", re.I), DesignSignal("systematic_review_or_meta_analysis", "high", 90, "Systematic-review or meta-analysis language is explicit.")),
    (re.compile(r"\b(randomized|randomised)\b.*\bphase\s*(iii|3)\b|\bphase\s*(iii|3)\b.*\b(randomized|randomised)\b", re.I | re.S), DesignSignal("randomized_phase_3_trial", "high", 88, "Randomization and phase III/3 are explicit.")),
    (re.compile(r"\b(randomized|randomised)\b", re.I), DesignSignal("randomized_trial", "high", 82, "Randomization is explicit.")),
    (re.compile(r"\bprospective\b.*\b(cohort|study)\b|\b(cohort|study)\b.*\bprospective\b", re.I | re.S), DesignSignal("prospective_cohort", "moderate", 68, "Prospective cohort/study language is explicit.")),
    (re.compile(r"\bretrospective\b.*\b(cohort|study|analysis)\b|\b(cohort|study|analysis)\b.*\bretrospective\b", re.I | re.S), DesignSignal("retrospective_study", "limited", 48, "Retrospective study/analysis language is explicit.")),
    (re.compile(r"\bcohort\b", re.I), DesignSignal("cohort_study", "moderate", 60, "Cohort language is explicit.")),
    (re.compile(r"\bcase report\b", re.I), DesignSignal("case_report", "limited", 25, "Case-report language is explicit.")),
)


def _combined_text(publication: ScientificPublication, passages: list[ScientificPassage]) -> str:
    return " ".join([publication.title, *[p.text for p in passages]])


def _design_signal(text: str) -> DesignSignal:
    for pattern, signal in _DESIGN_RULES:
        if pattern.search(text):
            return signal
    if re.search(r"\bphase\s*(iii|3)\b", text, re.I):
        return DesignSignal("phase_3_study", "moderate", 72, "Phase III/3 is explicit, but randomization is not explicit in the available text.")
    if re.search(r"\bphase\s*(ii|2)\b", text, re.I):
        return DesignSignal("phase_2_study", "moderate", 62, "Phase II/2 is explicit.")
    return DesignSignal("unspecified_from_available_text", "uncertain", 40, "Study design is not explicit in the available title/abstract text.")


def _sample_size(text: str) -> tuple[int | None, str | None]:
    patterns = (
        re.compile(r"\b(?:patients|participants|subjects)\s*(?:with[^.;:]{0,80})?\s*\(n\s*=\s*(\d{2,6})\)", re.I),
        re.compile(r"\b(?:n\s*=\s*)?(\d{2,6})\s+(?:patients|participants|subjects|tumou?rs)\b", re.I),
    )
    values: list[tuple[int, str]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = int(match.group(1))
            if value <= 100000:
                values.append((value, match.group(0)))
    if not values:
        return None, None
    value, evidence = max(values, key=lambda item: item[0])
    return value, evidence


def _sample_adjustment(sample_size: int | None) -> tuple[int, str]:
    if sample_size is None:
        return 0, "No defensible total sample size was detected from the available text."
    if sample_size >= 1000:
        return 10, f"Large reported sample size ({sample_size})."
    if sample_size >= 300:
        return 8, f"Substantial reported sample size ({sample_size})."
    if sample_size >= 100:
        return 6, f"Reported sample size is at least 100 ({sample_size})."
    if sample_size >= 50:
        return 3, f"Moderate reported sample size ({sample_size})."
    if sample_size < 20:
        return -4, f"Small reported sample size ({sample_size})."
    return 0, f"Reported sample size is {sample_size}."


def _method_signals(text: str) -> list[dict]:
    signals: list[dict] = []
    checks = (
        ("prospective", r"\bprospective\b", 4, "Prospective design is explicit."),
        ("randomized", r"\b(randomized|randomised)\b", 6, "Randomization is explicit."),
        ("registered_trial", r"\bNCT\d{8}\b", 4, "A ClinicalTrials.gov identifier is present."),
        ("paired_longitudinal_sampling", r"\bpaired\b.{0,100}\b(baseline|progression|follow[- ]?up|treatment discontinuation)\b", 3, "Paired longitudinal sampling is explicit."),
        ("multivariate_analysis", r"\bmultivariate\b", 3, "Multivariate analysis is explicit."),
        ("multi_region_sampling", r"\bmultiregion\b|\bmulti-region\b", 3, "Multi-region sampling is explicit."),
    )
    for name, pattern, points, rationale in checks:
        if re.search(pattern, text, re.I | re.S):
            signals.append({"name": name, "points": points, "rationale": rationale})
    return signals


def _quality_rating(score: int) -> str:
    if score >= 82:
        return "high"
    if score >= 65:
        return "moderate"
    if score >= 45:
        return "limited"
    return "very_limited"


def assess_publication_quality(publication: ScientificPublication, passages: list[ScientificPassage]) -> dict:
    text = _combined_text(publication, passages)
    design = _design_signal(text)
    sample_size, sample_evidence = _sample_size(text)
    sample_points, sample_rationale = _sample_adjustment(sample_size)
    method_signals = _method_signals(text)
    method_points = sum(signal["points"] for signal in method_signals)
    score = max(0, min(100, design.base_score + sample_points + method_points))

    observed_dimensions = 1 + int(sample_size is not None) + len(method_signals)
    assessment_confidence = min(0.95, 0.45 + observed_dimensions * 0.07)
    limitations = [
        "This is a deterministic evidence-quality signal, not a formal risk-of-bias assessment.",
        "The assessment is limited to metadata plus the title/abstract passages currently stored in YetSee.",
    ]
    if sample_size is None:
        limitations.append("Total study sample size could not be reliably determined from the available text.")
    if design.study_design == "unspecified_from_available_text":
        limitations.append("Study design was not explicit in the available text.")

    return {
        "publication_id": publication.id,
        "pmid": publication.pmid,
        "doi": publication.doi,
        "title": publication.title,
        "study_design": design.study_design,
        "evidence_level": design.evidence_level,
        "quality_score": score,
        "quality_rating": _quality_rating(score),
        "assessment_confidence": round(assessment_confidence, 2),
        "dimensions": {
            "design": {"score": design.base_score, "rationale": design.rationale},
            "sample_size": {"value": sample_size, "score_adjustment": sample_points, "evidence": sample_evidence, "rationale": sample_rationale},
            "method_signals": method_signals,
        },
        "limitations": limitations,
        "policy": {
            "derived_quality_assessment": True,
            "canonical_evidence": False,
            "formal_risk_of_bias": False,
            "algorithm": "deterministic-study-quality-v1",
        },
    }


def investigation_study_quality(db: Session, investigation_id: str) -> dict:
    if db.get(Investigation, investigation_id) is None:
        raise KeyError("Investigation not found")

    rows = db.execute(
        select(EvidenceLink, ScientificPassage, ScientificPublication)
        .join(ScientificPassage, EvidenceLink.scientific_passage_id == ScientificPassage.id)
        .join(ScientificPublication, ScientificPassage.publication_id == ScientificPublication.id)
        .where(EvidenceLink.investigation_id == investigation_id)
        .order_by(EvidenceLink.created_at.asc())
    ).all()

    grouped: dict[str, tuple[ScientificPublication, list[ScientificPassage], list[EvidenceLink]]] = {}
    for link, passage, publication in rows:
        if publication.id not in grouped:
            grouped[publication.id] = (publication, [], [])
        grouped[publication.id][1].append(passage)
        grouped[publication.id][2].append(link)

    studies = []
    for publication, passages, links in grouped.values():
        assessment = assess_publication_quality(publication, passages)
        assessment["investigation_evidence"] = {
            "stances": sorted({link.stance for link in links}),
            "evidence_link_count": len(links),
            "passage_count": len(passages),
        }
        studies.append(assessment)

    studies.sort(key=lambda item: (-item["quality_score"], item["title"]))
    if studies:
        scores = [item["quality_score"] for item in studies]
        mean_score = round(sum(scores) / len(scores), 1)
        high_or_moderate = sum(item["quality_rating"] in {"high", "moderate"} for item in studies)
    else:
        mean_score = 0.0
        high_or_moderate = 0

    return {
        "investigation_id": investigation_id,
        "study_count": len(studies),
        "mean_quality_score": mean_score,
        "high_or_moderate_quality_count": high_or_moderate,
        "studies": studies,
        "policy": {
            "derived_quality_assessment": True,
            "does_not_change_evidence_count": True,
            "formal_risk_of_bias": False,
            "algorithm": "deterministic-study-quality-v1",
        },
    }
