from app.mission_runtime.resolutions import compare_resolution_snapshots


def snapshot(*, contradictions=0, gaps=0, coverage=1.0, confidence=0.8, evidence=None):
    return {
        "contradiction_count": contradictions,
        "evidence_gap_count": gaps,
        "evidence_coverage": coverage,
        "confidence": confidence,
        "evidence_ids": evidence or [],
    }


def test_disagreement_is_resolved_when_followup_removes_all_contradictions():
    result = compare_resolution_snapshots(
        snapshot(contradictions=2, gaps=1, coverage=0.6, evidence=["e1"]),
        snapshot(contradictions=0, gaps=1, coverage=0.7, evidence=["e1", "e2"]),
        "resolve_agent_disagreement",
    )
    assert result["status"] == "resolved"
    assert result["objective_satisfied"] is True
    assert result["delta"]["contradiction_delta"] == -2
    assert result["evidence_added_ids"] == ["e2"]
    assert result["resolution_score"] > 0


def test_partial_disagreement_reduction_is_improved_not_resolved():
    result = compare_resolution_snapshots(
        snapshot(contradictions=2, coverage=0.6, evidence=["e1"]),
        snapshot(contradictions=1, coverage=0.7, evidence=["e1", "e2"]),
        "resolve_agent_disagreement",
    )
    assert result["status"] == "improved"
    assert result["objective_satisfied"] is False


def test_unchanged_followup_is_persisting():
    before = snapshot(contradictions=1, gaps=1, coverage=0.5, confidence=0.7, evidence=["e1"])
    result = compare_resolution_snapshots(before, dict(before), "resolve_agent_disagreement")
    assert result["status"] == "persisting"
    assert result["objective_satisfied"] is False
    assert result["resolution_score"] == 0


def test_new_contradiction_marks_followup_worsened():
    result = compare_resolution_snapshots(
        snapshot(contradictions=1, gaps=0, coverage=0.8, evidence=["e1"]),
        snapshot(contradictions=2, gaps=0, coverage=0.8, evidence=["e1"]),
        "resolve_agent_disagreement",
    )
    assert result["status"] == "worsened"
    assert result["objective_satisfied"] is False
    assert result["resolution_score"] < 0


def test_evidence_gap_action_requires_gap_reduction_and_new_evidence():
    resolved = compare_resolution_snapshots(
        snapshot(gaps=2, coverage=0.5, evidence=["e1"]),
        snapshot(gaps=1, coverage=0.75, evidence=["e1", "e2"]),
        "collect_independent_evidence",
    )
    not_resolved = compare_resolution_snapshots(
        snapshot(gaps=2, coverage=0.5, evidence=["e1"]),
        snapshot(gaps=1, coverage=0.75, evidence=["e1"]),
        "collect_independent_evidence",
    )
    assert resolved["status"] == "resolved"
    assert resolved["objective_satisfied"] is True
    assert not_resolved["status"] == "improved"
    assert not_resolved["objective_satisfied"] is False


def test_source_diversity_action_requires_added_evidence_without_coverage_regression():
    result = compare_resolution_snapshots(
        snapshot(coverage=0.6, evidence=["e1"]),
        snapshot(coverage=0.6, evidence=["e1", "e2"]),
        "expand_source_diversity",
    )
    assert result["status"] == "resolved"
    assert result["objective_satisfied"] is True
    assert result["evidence_added_ids"] == ["e2"]


def test_removed_evidence_is_preserved_in_resolution_delta():
    result = compare_resolution_snapshots(
        snapshot(evidence=["e1", "e2", "e3"]),
        snapshot(evidence=["e2", "e4"]),
        "re_evaluate_investigation",
    )
    assert result["evidence_added_ids"] == ["e4"]
    assert result["evidence_removed_ids"] == ["e1", "e3"]


def test_score_is_bounded_for_large_changes():
    improved = compare_resolution_snapshots(
        snapshot(contradictions=10, gaps=10, coverage=0.0),
        snapshot(contradictions=0, gaps=0, coverage=1.0, evidence=["e1"]),
        "resolve_agent_disagreement",
    )
    worsened = compare_resolution_snapshots(
        snapshot(contradictions=0, gaps=0, coverage=1.0),
        snapshot(contradictions=10, gaps=10, coverage=0.0),
        "resolve_agent_disagreement",
    )
    assert improved["resolution_score"] == 1.0
    assert worsened["resolution_score"] == -1.0
