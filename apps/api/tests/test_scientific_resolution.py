from app.mission_runtime.resolutions import compare_resolution_snapshots


def snapshot(*, contradictions=0, gaps=0, coverage=0.0, confidence=0.7, evidence=None):
    return {
        "contradiction_count": contradictions,
        "evidence_gap_count": gaps,
        "evidence_coverage": coverage,
        "confidence": confidence,
        "evidence_ids": evidence or [],
    }


def test_collect_independent_evidence_requires_gap_reduction_and_new_evidence():
    before = snapshot(gaps=2, coverage=0.5, evidence=["e1"])
    after = snapshot(gaps=1, coverage=0.75, evidence=["e1", "e2"])

    result = compare_resolution_snapshots(before, after, "collect_independent_evidence")

    assert result["objective_satisfied"] is True
    assert result["status"] == "resolved"
    assert result["evidence_added_ids"] == ["e2"]
    assert result["delta"]["evidence_gap_delta"] == -1
    assert result["delta"]["evidence_coverage_delta"] == 0.25


def test_collect_independent_evidence_stays_open_when_gaps_persist_without_new_evidence():
    before = snapshot(gaps=2, coverage=0.5, evidence=["e1"])
    after = snapshot(gaps=2, coverage=0.5, evidence=["e1"])

    result = compare_resolution_snapshots(before, after, "collect_independent_evidence")

    assert result["objective_satisfied"] is False
    assert result["status"] == "persisting"
    assert result["resolution_score"] == 0.0


def test_followup_that_exposes_more_uncertainty_is_worsened():
    before = snapshot(contradictions=0, gaps=1, coverage=0.75, evidence=["e1", "e2"])
    after = snapshot(contradictions=1, gaps=2, coverage=0.5, evidence=["e1", "e2"])

    result = compare_resolution_snapshots(before, after, "collect_independent_evidence")

    assert result["objective_satisfied"] is False
    assert result["status"] == "worsened"
    assert result["delta"]["contradiction_delta"] == 1
    assert result["delta"]["evidence_gap_delta"] == 1
    assert result["delta"]["evidence_coverage_delta"] == -0.25


def test_resolve_agent_disagreement_requires_contradictions_to_reach_zero():
    before = snapshot(contradictions=1, gaps=1, coverage=0.7, evidence=["e1"])
    after = snapshot(contradictions=0, gaps=1, coverage=0.7, evidence=["e1"])

    result = compare_resolution_snapshots(before, after, "resolve_agent_disagreement")

    assert result["objective_satisfied"] is True
    assert result["status"] == "resolved"
    assert result["delta"]["contradiction_delta"] == -1
