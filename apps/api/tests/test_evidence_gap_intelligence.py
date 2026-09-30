from app.scientific_literature.evidence_gap_intelligence import assess_evidence_gaps


def test_no_scientific_evidence_is_critical_gap():
    gaps = assess_evidence_gaps(
        quality={"study_count": 0, "high_or_moderate_quality_count": 0},
        hierarchy={"studies": [], "question_type": "mechanism"},
        independence={"overall_status": "single_publication", "publication_count": 0},
        contradiction={"groups": []},
    )
    assert len(gaps) == 1
    assert gaps[0]["gap_type"] == "no_scientific_evidence"
    assert gaps[0]["priority"] == "critical"


def test_single_publication_creates_replication_gap():
    gaps = assess_evidence_gaps(
        quality={"study_count": 1, "high_or_moderate_quality_count": 1, "mean_quality_score": 88},
        hierarchy={
            "question_type": "treatment_effect",
            "study_count": 1,
            "studies": [{"question_fit": "direct"}],
        },
        independence={"overall_status": "single_publication", "publication_count": 1},
        contradiction={"groups": []},
    )
    assert any(gap["gap_type"] == "replication_gap" for gap in gaps)


def test_confirmed_independent_direct_evidence_has_no_independence_or_fit_gap():
    gaps = assess_evidence_gaps(
        quality={"study_count": 2, "high_or_moderate_quality_count": 2, "mean_quality_score": 90},
        hierarchy={
            "question_type": "mechanism",
            "study_count": 2,
            "studies": [
                {"question_fit": "direct"},
                {"question_fit": "strong"},
            ],
        },
        independence={
            "overall_status": "confirmed_independent_trials",
            "publication_count": 2,
            "confirmed_independent_pair_count": 1,
            "same_trial_pair_count": 0,
            "unresolved_pair_count": 0,
        },
        contradiction={"groups": []},
    )
    gap_types = {gap["gap_type"] for gap in gaps}
    assert "independence_gap" not in gap_types
    assert "question_fit_gap" not in gap_types
    assert "quality_gap" not in gap_types


def test_pending_agreement_and_single_source_claims_create_review_and_replication_gaps():
    gaps = assess_evidence_gaps(
        quality={"study_count": 2, "high_or_moderate_quality_count": 2, "mean_quality_score": 88.5},
        hierarchy={
            "question_type": "mechanism",
            "study_count": 2,
            "studies": [{"question_fit": "direct"}, {"question_fit": "supportive"}],
        },
        independence={
            "overall_status": "confirmed_independent_trials",
            "publication_count": 2,
            "confirmed_independent_pair_count": 1,
            "same_trial_pair_count": 0,
            "unresolved_pair_count": 0,
        },
        contradiction={
            "provisional_agreement_group_count": 1,
            "provisional_tension_group_count": 0,
            "reviewed_contradiction_group_count": 0,
            "contextual_divergence_group_count": 1,
            "groups": [
                {"overall_status": "provisional_agreement"},
                {"overall_status": "single_source", "relationship": {"subject": {"name": "EGFR C797X mutation"}}},
            ],
        },
    )
    gap_types = {gap["gap_type"] for gap in gaps}
    assert "review_maturity_gap" in gap_types
    assert "claim_replication_gap" in gap_types
    assert "context_resolution_gap" in gap_types


def test_provisional_tension_is_high_priority():
    gaps = assess_evidence_gaps(
        quality={"study_count": 2, "high_or_moderate_quality_count": 2, "mean_quality_score": 80},
        hierarchy={
            "question_type": "mechanism",
            "study_count": 2,
            "studies": [{"question_fit": "direct"}, {"question_fit": "direct"}],
        },
        independence={
            "overall_status": "confirmed_independent_trials",
            "publication_count": 2,
            "confirmed_independent_pair_count": 1,
            "same_trial_pair_count": 0,
            "unresolved_pair_count": 0,
        },
        contradiction={
            "provisional_agreement_group_count": 0,
            "provisional_tension_group_count": 1,
            "reviewed_contradiction_group_count": 0,
            "contextual_divergence_group_count": 0,
            "groups": [],
        },
    )
    tension = next(gap for gap in gaps if gap["gap_type"] == "unresolved_tension")
    assert tension["priority"] == "high"
