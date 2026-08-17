from __future__ import annotations

from enum import StrEnum


class InvestigationState(StrEnum):
    NEW = "new"
    COLLECTING = "collecting"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    MONITORING = "monitoring"
    SIMULATING = "simulating"
    RECOMMENDING = "recommending"
    LEARNING = "learning"
    ARCHIVED = "archived"


_ALLOWED: dict[InvestigationState, set[InvestigationState]] = {
    InvestigationState.NEW: {InvestigationState.COLLECTING, InvestigationState.ARCHIVED},
    InvestigationState.COLLECTING: {InvestigationState.UNDER_REVIEW, InvestigationState.MONITORING, InvestigationState.ARCHIVED},
    InvestigationState.UNDER_REVIEW: {InvestigationState.ACTIVE, InvestigationState.COLLECTING, InvestigationState.ARCHIVED},
    InvestigationState.ACTIVE: {InvestigationState.MONITORING, InvestigationState.SIMULATING, InvestigationState.RECOMMENDING, InvestigationState.ARCHIVED},
    InvestigationState.MONITORING: {InvestigationState.ACTIVE, InvestigationState.SIMULATING, InvestigationState.RECOMMENDING, InvestigationState.ARCHIVED},
    InvestigationState.SIMULATING: {InvestigationState.ACTIVE, InvestigationState.MONITORING, InvestigationState.RECOMMENDING, InvestigationState.ARCHIVED},
    InvestigationState.RECOMMENDING: {InvestigationState.ACTIVE, InvestigationState.MONITORING, InvestigationState.LEARNING, InvestigationState.ARCHIVED},
    InvestigationState.LEARNING: {InvestigationState.MONITORING, InvestigationState.ACTIVE, InvestigationState.ARCHIVED},
    InvestigationState.ARCHIVED: {InvestigationState.MONITORING},
}


def normalize_state(value: str) -> InvestigationState:
    aliases = {
        "emerging": InvestigationState.COLLECTING,
        "watch": InvestigationState.COLLECTING,
        "candidate": InvestigationState.UNDER_REVIEW,
        "resolved": InvestigationState.LEARNING,
    }
    if value in aliases:
        return aliases[value]
    return InvestigationState(value)


def can_transition(current: str, target: str) -> bool:
    current_state = normalize_state(current)
    target_state = normalize_state(target)
    return target_state == current_state or target_state in _ALLOWED[current_state]


def allowed_transitions(current: str) -> list[str]:
    state = normalize_state(current)
    return sorted(item.value for item in _ALLOWED[state])
