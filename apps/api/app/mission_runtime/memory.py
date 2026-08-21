from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mission import ScientificDecision, ScientificMemory, ScientificResolution

COMPILER_VERSION = "1.0"


def compile_memory_lesson(resolution: ScientificResolution, decision: ScientificDecision) -> dict:
    before = resolution.before_json or {}
    after = resolution.after_json or {}
    delta = resolution.delta_json or {}
    added = sorted(set(resolution.evidence_added_ids or []))
    removed = sorted(set(resolution.evidence_removed_ids or []))

    contradiction_delta = int(delta.get("contradiction_delta") or 0)
    gap_delta = int(delta.get("evidence_gap_delta") or 0)
    coverage_delta = float(delta.get("evidence_coverage_delta") or 0)

    if resolution.objective_satisfied and decision.action_type == "resolve_agent_disagreement":
        memory_type = "disagreement_resolved"
        title = "Agent disagreement was resolved"
    elif resolution.objective_satisfied and decision.action_type == "collect_independent_evidence":
        memory_type = "evidence_gap_closed"
        title = "Independent evidence closed an evidence gap"
    elif resolution.objective_satisfied and decision.action_type == "expand_source_diversity":
        memory_type = "source_diversity_improved"
        title = "Broader evidence improved source diversity"
    elif resolution.status == "worsened":
        memory_type = "followup_worsened_uncertainty"
        title = "Follow-up investigation increased uncertainty"
    elif resolution.status == "persisting":
        memory_type = "uncertainty_persisted"
        title = "Scientific uncertainty persisted after follow-up"
    elif added:
        memory_type = "new_evidence_improved_state"
        title = "New evidence improved the investigation state"
    else:
        memory_type = "investigation_state_improved"
        title = "Follow-up investigation improved the scientific state"

    evidence_ids = sorted(set((before.get("evidence_ids") or []) + (after.get("evidence_ids") or []) + added))
    confidence = min(0.99, max(0.5, 0.55 + abs(float(resolution.resolution_score or 0)) * 0.25 + (0.12 if resolution.objective_satisfied else 0)))
    summary = (
        f"{resolution.summary} Decision action {decision.action_type.replace('_', ' ')} "
        f"{'satisfied' if resolution.objective_satisfied else 'did not satisfy'} its objective."
    )
    return {
        "memory_type": memory_type,
        "outcome": resolution.status,
        "confidence": round(confidence, 4),
        "title": title,
        "summary": summary,
        "evidence_ids": evidence_ids,
        "lesson": {
            "canonical_evidence": False,
            "derived_context": True,
            "action_type": decision.action_type,
            "objective_satisfied": resolution.objective_satisfied,
            "resolution_score": resolution.resolution_score,
            "contradiction_before": int(before.get("contradiction_count") or 0),
            "contradiction_after": int(after.get("contradiction_count") or 0),
            "contradiction_delta": contradiction_delta,
            "evidence_gap_before": int(before.get("evidence_gap_count") or 0),
            "evidence_gap_after": int(after.get("evidence_gap_count") or 0),
            "evidence_gap_delta": gap_delta,
            "evidence_coverage_before": float(before.get("evidence_coverage") or 0),
            "evidence_coverage_after": float(after.get("evidence_coverage") or 0),
            "evidence_coverage_delta": coverage_delta,
            "evidence_added_ids": added,
            "evidence_removed_ids": removed,
        },
    }


def memory_relevance(memory: ScientificMemory, action_type: str) -> int:
    """Score advisory relevance without treating memory as evidence."""
    lesson = memory.lesson_json or {}
    score = 0
    if lesson.get("action_type") == action_type:
        score += 5
    if memory.memory_type in {"uncertainty_persisted", "followup_worsened_uncertainty"}:
        score += 3
    if memory.memory_type == "disagreement_resolved" and action_type == "resolve_agent_disagreement":
        score += 4
    if memory.memory_type == "evidence_gap_closed" and action_type == "collect_independent_evidence":
        score += 4
    if memory.memory_type == "source_diversity_improved" and action_type == "expand_source_diversity":
        score += 4
    if lesson.get("objective_satisfied"):
        score += 1
    return score


def advisory_memory_context(db: Session, investigation_id: str, action_type: str, limit: int = 3) -> dict:
    memories = list(db.scalars(
        select(ScientificMemory)
        .where(ScientificMemory.investigation_id == investigation_id)
        .order_by(ScientificMemory.created_at.desc())
        .limit(50)
    ))
    ranked = sorted(
        ((memory_relevance(memory, action_type), memory) for memory in memories),
        key=lambda item: (item[0], item[1].created_at),
        reverse=True,
    )
    selected = [memory for score, memory in ranked if score > 0][:limit]
    return {
        "canonical_evidence": False,
        "derived_context": True,
        "action_type": action_type,
        "memory_ids": [memory.id for memory in selected],
        "lessons": [
            {
                "memory_id": memory.id,
                "memory_type": memory.memory_type,
                "outcome": memory.outcome,
                "confidence": memory.confidence,
                "title": memory.title,
                "summary": memory.summary,
                "objective_satisfied": bool((memory.lesson_json or {}).get("objective_satisfied")),
                "prior_action_type": (memory.lesson_json or {}).get("action_type"),
                "lesson": dict(memory.lesson_json or {}),
            }
            for memory in selected
        ],
    }


def assess_strategy_from_memory(action_type: str, context: dict) -> dict:
    """Classify whether a proposed strategy should be reused, modified, avoided, or treated as novel.

    Scientific Memory is derived planning context only. This function does not read or alter
    canonical evidence and never changes scientific confidence.
    """
    lessons = context.get("lessons") or []
    same_action = [item for item in lessons if item.get("prior_action_type") == action_type]
    relevant = same_action or lessons
    canonical = {
        "canonical_evidence": False,
        "derived_context": True,
        "proposed_action_type": action_type,
        "relevant_memory_ids": [item.get("memory_id") for item in relevant if item.get("memory_id")],
        "prior_action_types": sorted({item.get("prior_action_type") for item in relevant if item.get("prior_action_type")}),
        "prior_outcomes": [item.get("outcome") for item in relevant if item.get("outcome")],
    }
    if not relevant:
        return {
            **canonical,
            "strategy_class": "novel_strategy",
            "repeat_risk": "low",
            "rationale": "No relevant prior scientific memory was found for this action.",
            "adaptation": "Proceed with the proposed strategy and compare its outcome against future scientific memory.",
        }

    successful_same = [item for item in same_action if item.get("objective_satisfied")]
    failed_same = [item for item in same_action if item.get("outcome") in {"worsened", "persisting"} or not item.get("objective_satisfied")]

    if successful_same and not failed_same:
        return {
            **canonical,
            "strategy_class": "reuse",
            "repeat_risk": "low",
            "rationale": "The same scientific action previously satisfied its objective.",
            "adaptation": "Reuse the prior strategy where the current scientific conditions are sufficiently similar.",
        }

    if failed_same:
        worst = failed_same[0]
        lesson = worst.get("lesson") or {}
        added = len(lesson.get("evidence_added_ids") or [])
        gap_before = int(lesson.get("evidence_gap_before") or 0)
        gap_after = int(lesson.get("evidence_gap_after") or 0)
        contradiction_delta = int(lesson.get("contradiction_delta") or 0)
        coverage_delta = float(lesson.get("evidence_coverage_delta") or 0)
        exact_repeat_failed = added == 0 and gap_after >= gap_before and coverage_delta <= 0 and contradiction_delta >= 0
        if exact_repeat_failed:
            return {
                **canonical,
                "strategy_class": "avoid_exact_repeat",
                "repeat_risk": "high",
                "rationale": (
                    f"The same action previously produced {added} new evidence link(s), evidence gaps {gap_before}→{gap_after}, "
                    f"and contradiction delta {contradiction_delta:+d}."
                ),
                "adaptation": "Change the evidence acquisition method, target the unresolved claim directly, or use a different independent source before repeating the mission.",
            }
        return {
            **canonical,
            "strategy_class": "modify",
            "repeat_risk": "medium",
            "rationale": "The same action was attempted previously but did not satisfy the scientific objective.",
            "adaptation": "Modify the mission scope or evidence strategy rather than repeating the prior follow-up unchanged.",
        }

    return {
        **canonical,
        "strategy_class": "modify",
        "repeat_risk": "medium",
        "rationale": "Relevant scientific memory exists, but it does not establish a clearly successful reusable strategy.",
        "adaptation": "Use the prior lesson to adjust the mission and explicitly compare the new outcome with the previous one.",
    }


def apply_memory_to_objective(objective: str, context: dict, assessment: dict | None = None) -> str:
    """Make memory influence explicit in the mission objective, never implicit."""
    lessons = context.get("lessons") or []
    if not lessons:
        return objective
    assessment = assessment or assess_strategy_from_memory(context.get("action_type") or "", context)
    strategy = assessment.get("strategy_class")
    if strategy == "avoid_exact_repeat":
        note = "avoid an exact repeat of the prior unsuccessful strategy; change the evidence source, acquisition method, or claim target"
    elif strategy == "modify":
        note = "modify the prior strategy using the recorded scientific lesson"
    elif strategy == "reuse":
        note = "reuse the previously successful strategy where scientifically applicable"
    else:
        note = "compare the new outcome against prior scientific memory"
    return f"{objective} Prior scientific memory is advisory only: {note}."


def compile_scientific_memory(db: Session, resolution_id: str) -> ScientificMemory:
    resolution = db.get(ScientificResolution, resolution_id)
    if resolution is None:
        raise KeyError("Scientific resolution not found")
    existing = db.scalar(select(ScientificMemory).where(ScientificMemory.resolution_id == resolution.id))
    if existing is not None:
        return existing
    decision = db.get(ScientificDecision, resolution.decision_id)
    if decision is None:
        raise KeyError("Scientific decision not found")

    compiled = compile_memory_lesson(resolution, decision)
    memory = ScientificMemory(
        investigation_id=resolution.investigation_id,
        resolution_id=resolution.id,
        decision_id=resolution.decision_id,
        parent_mission_id=resolution.parent_mission_id,
        followup_mission_id=resolution.followup_mission_id,
        memory_type=compiled["memory_type"],
        outcome=compiled["outcome"],
        compiler_version=COMPILER_VERSION,
        confidence=compiled["confidence"],
        title=compiled["title"],
        summary=compiled["summary"],
        lesson_json=compiled["lesson"],
        source_synthesis_finding_ids=[resolution.parent_synthesis_finding_id, resolution.followup_synthesis_finding_id],
        evidence_ids=compiled["evidence_ids"],
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def list_scientific_memories(db: Session, investigation_id: str, limit: int = 50) -> list[ScientificMemory]:
    return list(db.scalars(select(ScientificMemory).where(
        ScientificMemory.investigation_id == investigation_id
    ).order_by(ScientificMemory.created_at.desc()).limit(limit)))
