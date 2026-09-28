from app.scientific_literature.question_evidence_hierarchy import assess_question_fit, classify_scientific_question


def study(design, signals=None, quality=70, sample_size=None):
    return {
        "study_design": design,
        "quality_score": quality,
        "dimensions": {
            "method_signals": [{"name": name, "points": 0, "rationale": ""} for name in (signals or [])],
            "sample_size": {"value": sample_size},
        },
    }


def test_mechanism_question_is_classified_deterministically():
    result=classify_scientific_question("What mechanisms contribute to acquired resistance to osimertinib?")
    assert result.question_type=="mechanism"
    assert result.confidence==0.9


def test_paired_longitudinal_mechanism_study_can_outfit_generic_rct():
    paired=assess_question_fit("mechanism",study("phase_3_study",["paired_longitudinal_sampling"]))
    randomized=assess_question_fit("mechanism",study("randomized_phase_3_trial",["randomized"]))
    assert paired["question_fit_score"]==90
    assert paired["question_fit"]=="direct"
    assert randomized["question_fit_score"]==60
    assert randomized["question_fit"]=="supportive"


def test_randomized_trial_is_direct_fit_for_treatment_effect():
    result=assess_question_fit("treatment_effect",study("randomized_phase_3_trial",["randomized"],98))
    assert result["question_fit_score"]==90
    assert result["question_fit"]=="direct"


def test_general_question_does_not_invent_specialized_hierarchy():
    classification=classify_scientific_question("What does the current evidence show?")
    result=assess_question_fit(classification.question_type,study("cohort_study"))
    assert classification.question_type=="general_scientific"
    assert classification.confidence==0.5
    assert result["question_fit_score"]==60
    assert result["question_fit"]=="supportive"
