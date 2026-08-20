from types import SimpleNamespace

from app.mission_runtime.memory import compile_memory_lesson


def resolution(**overrides):
    values = {
        "before_json": {"contradiction_count": 1, "evidence_gap_count": 1, "evidence_coverage": 0.5, "evidence_ids": ["e1"]},
        "after_json": {"contradiction_count": 0, "evidence_gap_count": 0, "evidence_coverage": 1.0, "evidence_ids": ["e1", "e2"]},
        "delta_json": {"contradiction_delta": -1, "evidence_gap_delta": -1, "evidence_coverage_delta": 0.5},
        "evidence_added_ids": ["e2"],
        "evidence_removed_ids": [],
        "objective_satisfied": True,
        "resolution_score": 0.8,
        "status": "resolved",
        "summary": "Follow-up resolved the scientific objective.",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def decision(action_type):
    return SimpleNamespace(action_type=action_type)


def test_resolved_disagreement_compiles_explicit_memory():
    memory = compile_memory_lesson(resolution(), decision("resolve_agent_disagreement"))
    assert memory["memory_type"] == "disagreement_resolved"
    assert memory["outcome"] == "resolved"
    assert memory["lesson"]["canonical_evidence"] is False
    assert memory["lesson"]["derived_context"] is True
    assert memory["evidence_ids"] == ["e1", "e2"]


def test_closed_evidence_gap_compiles_distinct_lesson():
    memory = compile_memory_lesson(resolution(), decision("collect_independent_evidence"))
    assert memory["memory_type"] == "evidence_gap_closed"


def test_persisting_uncertainty_is_not_mislabeled_as_success():
    memory = compile_memory_lesson(
        resolution(status="persisting", objective_satisfied=False, resolution_score=0.0, evidence_added_ids=[]),
        decision("resolve_agent_disagreement"),
    )
    assert memory["memory_type"] == "uncertainty_persisted"
    assert memory["outcome"] == "persisting"


def test_worsened_followup_becomes_warning_memory():
    memory = compile_memory_lesson(
        resolution(status="worsened", objective_satisfied=False, resolution_score=-0.5),
        decision("re_evaluate_investigation"),
    )
    assert memory["memory_type"] == "followup_worsened_uncertainty"
    assert memory["confidence"] >= 0.5


def test_added_evidence_is_preserved_as_provenance_not_promoted_to_memory_evidence():
    memory = compile_memory_lesson(
        resolution(status="improved", objective_satisfied=False, evidence_added_ids=["e3"]),
        decision("re_evaluate_investigation"),
    )
    assert memory["memory_type"] == "new_evidence_improved_state"
    assert "e3" in memory["evidence_ids"]
    assert memory["lesson"]["canonical_evidence"] is False
