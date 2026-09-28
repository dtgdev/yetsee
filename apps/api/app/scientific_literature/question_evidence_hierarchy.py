from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.scientific_literature.study_quality import investigation_study_quality


@dataclass(frozen=True)
class QuestionClassification:
    question_type: str
    confidence: float
    rationale: str


_QUESTION_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("mechanism", re.compile(r"\b(mechanism|mechanisms|pathway|pathways|resistance|mediates?|drives?|causes?)\b", re.I), "Mechanistic language is explicit in the research question."),
    ("treatment_effect", re.compile(r"\b(efficacy|effective|improve|benefit|treatment|therapy|survival|response|outcome)\b", re.I), "Treatment-effect or clinical-outcome language is explicit."),
    ("diagnostic_accuracy", re.compile(r"\b(diagnostic|diagnosis|sensitivity|specificity|predictive value|screening|detect)\b", re.I), "Diagnostic-performance language is explicit."),
    ("prognosis", re.compile(r"\b(prognosis|prognostic|predicts?|risk of progression|recurrence|mortality)\b", re.I), "Prognostic language is explicit."),
    ("prevalence", re.compile(r"\b(prevalence|incidence|frequency|how common|rate of)\b", re.I), "Frequency or population-burden language is explicit."),
    ("safety", re.compile(r"\b(safety|adverse|toxicity|harm|side effect)\b", re.I), "Safety or harm language is explicit."),
    ("association", re.compile(r"\b(associated|association|correlat|relationship between|risk factor)\b", re.I), "Association or risk-factor language is explicit."),
)


def classify_scientific_question(text: str) -> QuestionClassification:
    clean = " ".join((text or "").split())
    for question_type, pattern, rationale in _QUESTION_RULES:
        if pattern.search(clean):
            return QuestionClassification(question_type, 0.9, rationale)
    return QuestionClassification(
        "general_scientific",
        0.5,
        "The available research-question text does not contain a strong deterministic signal for a more specific question class.",
    )


def _signal_names(study: dict) -> set[str]:
    return {item["name"] for item in study.get("dimensions", {}).get("method_signals", [])}


def assess_question_fit(question_type: str, study: dict) -> dict:
    design = study.get("study_design", "unspecified_from_available_text")
    signals = _signal_names(study)
    score = 50
    reasons: list[str] = []

    if question_type == "mechanism":
        if "paired_longitudinal_sampling" in signals:
            score += 30
            reasons.append("Paired longitudinal sampling directly strengthens inference about acquired biological change.")
        if design in {"prospective_cohort", "cohort_study", "phase_2_study", "phase_3_study", "randomized_trial", "randomized_phase_3_trial"}:
            score += 10
            reasons.append("The design can support mechanistic observations when molecular measurements are collected.")
        if design in {"randomized_trial", "randomized_phase_3_trial"}:
            reasons.append("Randomization strengthens treatment comparisons but does not by itself establish a biological mechanism.")
        if design == "systematic_review_or_meta_analysis":
            score += 5
            reasons.append("Synthesis can summarize mechanistic evidence, but fit depends on the underlying mechanistic studies.")
    elif question_type == "treatment_effect":
        if design in {"randomized_trial", "randomized_phase_3_trial"}:
            score += 40
            reasons.append("Randomized comparative trials are a direct fit for treatment-effect questions.")
        elif design == "systematic_review_or_meta_analysis":
            score += 35
            reasons.append("Systematic synthesis is a strong fit when it pools eligible comparative treatment studies.")
        elif design in {"prospective_cohort", "cohort_study"}:
            score += 10
            reasons.append("Observational cohorts can inform treatment outcomes but are more vulnerable to confounding.")
    elif question_type == "diagnostic_accuracy":
        if design in {"prospective_cohort", "cohort_study"}:
            score += 25
            reasons.append("Cohort designs can directly estimate diagnostic performance when an appropriate reference standard is used.")
        if "prospective" in signals:
            score += 10
            reasons.append("Prospective ascertainment improves fit for diagnostic-performance evaluation.")
    elif question_type == "prognosis":
        if design in {"prospective_cohort", "cohort_study"}:
            score += 30
            reasons.append("Longitudinal cohort designs are a direct fit for prognosis questions.")
        if "multivariate_analysis" in signals:
            score += 10
            reasons.append("Multivariable analysis is relevant to adjusted prognostic estimation.")
    elif question_type == "prevalence":
        if design in {"cohort_study", "prospective_cohort", "retrospective_study"}:
            score += 20
            reasons.append("Population-based observational designs can estimate frequency when sampling is appropriate.")
    elif question_type == "safety":
        if design in {"randomized_trial", "randomized_phase_3_trial", "prospective_cohort", "cohort_study"}:
            score += 20
            reasons.append("The design can contribute safety observations, subject to follow-up duration and event ascertainment.")
        if study.get("dimensions", {}).get("sample_size", {}).get("value"):
            score += 5
            reasons.append("A reported sample size improves interpretability for observed adverse events.")
    elif question_type == "association":
        if design in {"prospective_cohort", "cohort_study", "retrospective_study"}:
            score += 25
            reasons.append("Observational analytic designs are directly relevant to association questions.")
        if "multivariate_analysis" in signals:
            score += 10
            reasons.append("Multivariable analysis can address measured confounding.")
    else:
        score = 60
        reasons.append("No specialized question hierarchy was applied; the generic study-quality signal remains primary.")

    score = max(0, min(100, score))
    if score >= 85:
        fit = "direct"
    elif score >= 70:
        fit = "strong"
    elif score >= 55:
        fit = "supportive"
    elif score >= 40:
        fit = "limited"
    else:
        fit = "poor"

    return {
        "question_fit_score": score,
        "question_fit": fit,
        "rationale": reasons or ["Available structured study signals are insufficient to establish a strong question-specific fit."],
    }


def investigation_question_evidence_hierarchy(db: Session, investigation_id: str) -> dict:
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError("Investigation not found")

    attributes = investigation.attributes or {}
    question = str(attributes.get("research_question") or investigation.summary or investigation.title)
    classification = classify_scientific_question(question)
    quality = investigation_study_quality(db, investigation_id)

    studies = []
    for study in quality["studies"]:
        fit = assess_question_fit(classification.question_type, study)
        studies.append({
            "publication_id": study["publication_id"],
            "pmid": study["pmid"],
            "doi": study["doi"],
            "title": study["title"],
            "study_design": study["study_design"],
            "generic_quality_score": study["quality_score"],
            "generic_quality_rating": study["quality_rating"],
            **fit,
        })

    studies.sort(key=lambda item: (-item["question_fit_score"], -item["generic_quality_score"], item["title"]))

    return {
        "investigation_id": investigation_id,
        "research_question": question,
        "question_type": classification.question_type,
        "classification_confidence": classification.confidence,
        "classification_rationale": classification.rationale,
        "study_count": len(studies),
        "studies": studies,
        "policy": {
            "question_specific_assessment": True,
            "generic_quality_is_not_universal_hierarchy": True,
            "canonical_evidence": False,
            "does_not_change_evidence_count": True,
            "algorithm": "deterministic-question-evidence-hierarchy-v1",
        },
    }
