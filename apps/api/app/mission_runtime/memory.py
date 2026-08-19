from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mission import ScientificDecision, ScientificMemory, ScientificResolution

COMPILER_VERSION = "1.0"


def compile_memory_lesson(resolution: ScientificResolution, decision: ScientificDecision) -> dict:
    """Compile one deterministic lesson from an immutable scientific resolution."""
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
