from app.mission_runtime.memory import assess_strategy_from_memory


def lesson(memory_id, *, action_type, outcome, objective_satisfied=False, added=None, gap_before=0, gap_after=0, contradiction_delta=0, coverage_delta=0.0):
    return {
        "memory_id": memory_id,
        "memory_type": "followup_worsened_uncertainty" if outcome == "worsened" else "uncertainty_persisted",
        "outcome": outcome,
        "objective_satisfied": objective_satisfied,
        "prior_action_type": action_type,
        "lesson": {
            "action_type": action_type,
            "objective_satisfied": objective_satisfied,
            "evidence_added_ids": added or [],
            "evidence_gap_before": gap_before,
            "evidence_gap_after": gap_after,
            "contradiction_delta": contradiction_delta,
            "evidence_coverage_delta": coverage_delta,
        },
    }


def test_no_memory_is_novel_strategy():
    result = assess_strategy_from_memory("collect_independent_evidence", {"lessons": []})

    assert result["strategy_class"] == "novel_strategy"
    assert result["repeat_risk"] == "low"
    assert result["canonical_evidence"] is False
    assert result["derived_context"] is True


def test_successful_same_action_is_reusable():
    context = {
        "lessons": [
            lesson(
                "m1",
                action_type="collect_independent_evidence",
                outcome="resolved",
                objective_satisfied=True,
                added=["e2"],
                gap_before=2,
                gap_after=1,
                coverage_delta=0.2,
            )
        ]
    }

    result = assess_strategy_from_memory("collect_independent_evidence", context)

    assert result["strategy_class"] == "reuse"
    assert result["repeat_risk"] == "low"
    assert result["relevant_memory_ids"] == ["m1"]


def test_running_clubs_failed_evidence_collection_avoids_exact_repeat():
    context = {
        "lessons": [
            lesson(
                "running-clubs-memory",
                action_type="collect_independent_evidence",
                outcome="worsened",
                added=[],
                gap_before=2,
                gap_after=2,
                contradiction_delta=1,
                coverage_delta=0.0,
            )
        ]
    }

    result = assess_strategy_from_memory("collect_independent_evidence", context)

    assert result["strategy_class"] == "avoid_exact_repeat"
    assert result["repeat_risk"] == "high"
    assert result["relevant_memory_ids"] == ["running-clubs-memory"]
    assert "0 new evidence" in result["rationale"]
    assert "2→2" in result["rationale"]
    assert "+1" in result["rationale"]


def test_failed_same_action_with_partial_improvement_is_modify_not_avoid():
    context = {
        "lessons": [
            lesson(
                "m2",
                action_type="collect_independent_evidence",
                outcome="persisting",
                added=["e-new"],
                gap_before=2,
                gap_after=1,
                contradiction_delta=0,
                coverage_delta=0.1,
            )
        ]
    }

    result = assess_strategy_from_memory("collect_independent_evidence", context)

    assert result["strategy_class"] == "modify"
    assert result["repeat_risk"] == "medium"


def test_different_prior_action_informs_modification_without_becoming_evidence():
    context = {
        "lessons": [
            lesson(
                "m3",
                action_type="expand_source_diversity",
                outcome="persisting",
                gap_before=1,
                gap_after=1,
            )
        ]
    }

    result = assess_strategy_from_memory("resolve_agent_disagreement", context)

    assert result["strategy_class"] == "modify"
    assert result["canonical_evidence"] is False
    assert result["prior_action_types"] == ["expand_source_diversity"]
