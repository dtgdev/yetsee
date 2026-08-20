from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mission_runtime.decisions import _legacy_synthesis_payload, _synthesis_finding_for_mission
from app.models.agent import AgentFinding
from app.models.mission import InvestigationMission, ScientificDecision, ScientificMemory, ScientificResolution


def _synthesis_payload(db: Session, mission: InvestigationMission, finding: AgentFinding) -> dict:
    """Return the synthesis payload bound to one exact persisted mission.

    Current missions store metadata_json.synthesis directly. Older Galileo missions
    are reconstructed only from finding IDs persisted on that mission's steps.
    """
    return (finding.metadata_json or {}).get("synthesis") or _legacy_synthesis_payload(db, mission, finding)


def _snapshot(finding: AgentFinding, synthesis: dict) -> dict:
    count = max(1, int(synthesis.get("finding_count") or 0))
    backed = int(synthesis.get("evidence_backed_count") or 0)
    return {
        "finding_id": finding.id,
        "confidence": float(finding.confidence or 0),
        "agreement_count": int(synthesis.get("agreement_count") or 0),
        "contradiction_count": int(synthesis.get("contradiction_count") or 0),
        "evidence_gap_count": int(synthesis.get("evidence_gap_count") or 0),
        "evidence_backed_count": backed,
        "finding_count": int(synthesis.get("finding_count") or 0),
        "evidence_coverage": round(backed / count, 4),
        "evidence_ids": sorted(set(synthesis.get("evidence_ids") or [])),
        "recommendation": (finding.metadata_json or {}).get("recommendation"),
        "legacy_reconstructed": bool(synthesis.get("legacy_reconstructed")),
    }


def compare_resolution_snapshots(before: dict, after: dict, action_type: str) -> dict:
    """Deterministically compare two persisted synthesis snapshots.

    This function contains the scientific-resolution classification contract and
    intentionally has no database or model dependencies.
    """
    contradiction_delta = int(after.get("contradiction_count") or 0) - int(before.get("contradiction_count") or 0)
    gap_delta = int(after.get("evidence_gap_count") or 0) - int(before.get("evidence_gap_count") or 0)
    coverage_delta = round(float(after.get("evidence_coverage") or 0) - float(before.get("evidence_coverage") or 0), 4)
    confidence_delta = round(float(after.get("confidence") or 0) - float(before.get("confidence") or 0), 4)
    before_evidence = set(before.get("evidence_ids") or [])
    after_evidence = set(after.get("evidence_ids") or [])
    added = sorted(after_evidence - before_evidence)
    removed = sorted(before_evidence - after_evidence)

    objective_satisfied = False
    if action_type == "resolve_agent_disagreement":
        objective_satisfied = int(before.get("contradiction_count") or 0) > 0 and int(after.get("contradiction_count") or 0) == 0
    elif action_type == "collect_independent_evidence":
        objective_satisfied = int(after.get("evidence_gap_count") or 0) < int(before.get("evidence_gap_count") or 0) and bool(added)
    elif action_type == "expand_source_diversity":
        objective_satisfied = bool(added) and float(after.get("evidence_coverage") or 0) >= float(before.get("evidence_coverage") or 0)
    elif action_type == "human_review":
        objective_satisfied = int(after.get("contradiction_count") or 0) == 0 and int(after.get("evidence_gap_count") or 0) == 0
    else:
        objective_satisfied = contradiction_delta <= 0 and gap_delta <= 0 and (coverage_delta > 0 or bool(added))

    improvement = (int(before.get("contradiction_count") or 0) - int(after.get("contradiction_count") or 0)) * 0.35
    improvement += (int(before.get("evidence_gap_count") or 0) - int(after.get("evidence_gap_count") or 0)) * 0.25
    improvement += coverage_delta * 0.25 + max(0.0, confidence_delta) * 0.15
    regression = max(0, contradiction_delta) * 0.35 + max(0, gap_delta) * 0.25 + max(0.0, -coverage_delta) * 0.25
    score = round(max(-1.0, min(1.0, improvement - regression)), 4)

    if objective_satisfied:
        status = "resolved"
    elif contradiction_delta > 0 or gap_delta > 0 or coverage_delta < -0.05:
        status = "worsened"
    elif contradiction_delta < 0 or gap_delta < 0 or coverage_delta > 0.05 or added:
        status = "improved"
    else:
        status = "persisting"

    return {
        "status": status,
        "objective_satisfied": objective_satisfied,
        "resolution_score": score,
        "delta": {
            "contradiction_delta": contradiction_delta,
            "evidence_gap_delta": gap_delta,
            "evidence_coverage_delta": coverage_delta,
            "confidence_delta": confidence_delta,
        },
        "evidence_added_ids": added,
        "evidence_removed_ids": removed,
    }


def _apply_resolution(
    resolution: ScientificResolution,
    decision: ScientificDecision,
    followup: InvestigationMission,
    parent_finding: AgentFinding,
    followup_finding: AgentFinding,
    before: dict,
    after: dict,
    comparison: dict,
) -> None:
    resolution.investigation_id = decision.investigation_id
    resolution.parent_mission_id = decision.mission_id
    resolution.followup_mission_id = followup.id
    resolution.parent_synthesis_finding_id = parent_finding.id
    resolution.followup_synthesis_finding_id = followup_finding.id
    resolution.status = comparison["status"]
    resolution.objective_satisfied = comparison["objective_satisfied"]
    resolution.resolution_score = comparison["resolution_score"]
    resolution.summary = (
        f"Follow-up mission {comparison['status']}: contradictions {before['contradiction_count']}→{after['contradiction_count']}, "
        f"evidence gaps {before['evidence_gap_count']}→{after['evidence_gap_count']}, "
        f"evidence coverage {round(before['evidence_coverage']*100)}%→{round(after['evidence_coverage']*100)}%, "
        f"with {len(comparison['evidence_added_ids'])} new evidence link(s)."
    )
    resolution.before_json = before
    resolution.after_json = after
    resolution.delta_json = comparison["delta"]
    resolution.evidence_added_ids = comparison["evidence_added_ids"]
    resolution.evidence_removed_ids = comparison["evidence_removed_ids"]


def assess_scientific_resolution(db: Session, decision_id: str) -> ScientificResolution:
    decision = db.get(ScientificDecision, decision_id)
    if decision is None:
        raise KeyError("Scientific decision not found")
    if not decision.next_mission_id:
        raise ValueError("Decision has no follow-up mission")

    parent = db.get(InvestigationMission, decision.mission_id)
    followup = db.get(InvestigationMission, decision.next_mission_id)
    if parent is None:
        raise KeyError("Parent mission not found")
    if followup is None:
        raise KeyError("Follow-up mission not found")
    if followup.status != "completed":
        raise ValueError("Resolution requires a completed follow-up mission")

    parent_finding = db.get(AgentFinding, decision.synthesis_finding_id)
    followup_finding = _synthesis_finding_for_mission(db, followup)
    if parent_finding is None or followup_finding is None:
        raise ValueError("Both parent and follow-up missions require persisted synthesis findings")

    parent_synthesis = _synthesis_payload(db, parent, parent_finding)
    followup_synthesis = _synthesis_payload(db, followup, followup_finding)
    if not parent_synthesis or not followup_synthesis:
        raise ValueError("Both parent and follow-up synthesis payloads must be reconstructable from their mission lineage")

    before = _snapshot(parent_finding, parent_synthesis)
    after = _snapshot(followup_finding, followup_synthesis)
    comparison = compare_resolution_snapshots(before, after, decision.action_type)

    existing = db.scalar(select(ScientificResolution).where(ScientificResolution.decision_id == decision.id))
    if existing is not None:
        compiled_memory = db.scalar(select(ScientificMemory).where(ScientificMemory.resolution_id == existing.id))
        if compiled_memory is not None:
            return existing
        # Correct pre-memory resolution artifacts produced by the historical
        # investigation-wide synthesis lookup bug. No scientific memory has yet
        # been compiled from this record, so replacing the deterministic snapshot
        # fields repairs provenance without rewriting canonical evidence.
        _apply_resolution(existing, decision, followup, parent_finding, followup_finding, before, after, comparison)
        db.commit()
        db.refresh(existing)
        return existing

    resolution = ScientificResolution(
        investigation_id=decision.investigation_id,
        decision_id=decision.id,
        parent_mission_id=decision.mission_id,
        followup_mission_id=followup.id,
        parent_synthesis_finding_id=parent_finding.id,
        followup_synthesis_finding_id=followup_finding.id,
        status=comparison["status"],
        objective_satisfied=comparison["objective_satisfied"],
        resolution_score=comparison["resolution_score"],
        summary="",
        before_json={},
        after_json={},
        delta_json={},
        evidence_added_ids=[],
        evidence_removed_ids=[],
    )
    _apply_resolution(resolution, decision, followup, parent_finding, followup_finding, before, after, comparison)
    db.add(resolution)
    db.commit()
    db.refresh(resolution)
    return resolution


def list_scientific_resolutions(db: Session, investigation_id: str, limit: int = 50) -> list[ScientificResolution]:
    return list(db.scalars(select(ScientificResolution).where(
        ScientificResolution.investigation_id == investigation_id
    ).order_by(ScientificResolution.created_at.desc()).limit(limit)))
