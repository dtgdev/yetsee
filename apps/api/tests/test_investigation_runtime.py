import pytest

from app.investigation_runtime.state import InvestigationState, allowed_transitions, can_transition, normalize_state


def test_legacy_states_normalize_into_runtime_states():
    assert normalize_state("emerging") == InvestigationState.COLLECTING
    assert normalize_state("candidate") == InvestigationState.UNDER_REVIEW


def test_lifecycle_allows_expected_progression():
    assert can_transition("new", "collecting")
    assert can_transition("collecting", "under_review")
    assert can_transition("under_review", "active")
    assert can_transition("active", "monitoring")
    assert can_transition("monitoring", "simulating")
    assert can_transition("simulating", "recommending")
    assert can_transition("recommending", "learning")


def test_lifecycle_rejects_invalid_jump():
    assert not can_transition("new", "recommending")
    assert "recommending" not in allowed_transitions("new")


def test_unknown_state_is_rejected():
    with pytest.raises(ValueError):
        normalize_state("teleporting")
