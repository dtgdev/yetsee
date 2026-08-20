from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import AgentFinding
from app.models.mission import InvestigationMission, ScientificDecision, ScientificResolution


def _synthesis_for_mission(db: Session, mission: InvestigationMission) -> AgentFinding | None:
    explicit = (mission.metadata_json or {}).get("synthesis_finding_id")
    if explicit:
        finding = db.get(AgentFinding, explicit)
        if finding is not None:
            return finding
    query = select(AgentFinding).where(
        AgentFinding.target_id == mission.investigation_id,
        AgentFinding.category == "investigation_synthesis",
    )
    if mission.started_at is not None:
        query = query.where(AgentFinding.created_at >= mission.started_at)
    if mission.finished_at is not None:
        query = query.where(AgentFinding.created_at <= mission.finished_at)
    return db.scalar(query.order_by(AgentFinding.created_at.desc()))


def _snapshot(finding: AgentFinding) -> dict:
    synthesis = (finding.metadata_json or {}).get("synthesis") or {}
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


def assess_scientific_resolution(db: Session, decision_id: str) -> ScientificResolution:
    decision = db.get(ScientificDecision, decision_id)
    if decision is None:
        raise KeyError("Scientific decision not found")
    if not decision.next_mission_id:
        raise ValueError("Decision has no follow-up mission")
    followup = db.get(InvestigationMission, decision.next_mission_id)
    if followup is None:
        raise KeyError("Follow-up mission not found")
    if followup.status != "completed":
        raise ValueError("Resolution requires a completed follow-up mission")

    existing = db.scalar(select(ScientificResolution).where(ScientificResolution.decision_id == decision.id))
    if existing is not None:
        return existing

    parent_finding = db.get(AgentFinding, decision.synthesis_finding_id)
    followup_finding = _synthesis_for_mission(db, followup)
    if parent_finding is None or followup_finding is None:
        raise ValueError("Both parent and follow-up missions require persisted synthesis findings")

    before = _snapshot(parent_finding)
    after = _snapshot(followup_finding)
    comparison = compare_resolution_snapshots(before, after, decision.action_type)

    summary = (
        f"Follow-up mission {comparison['status']}: contradictions {before['contradiction_count']}→{after['contradiction_count']}, "
        f"evidence gaps {before['evidence_gap_count']}→{after['evidence_gap_count']}, "
        f"evidence coverage {round(before['evidence_coverage']*100)}%→{round(after['evidence_coverage']*100)}%, "
        f"with {len(comparison['evidence_added_ids'])} new evidence link(s)."
    )
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
        summary=summary,
        before_json=before,
        after_json=after,
        delta_json=comparison["delta"],
        evidence_added_ids=comparison["evidence_added_ids"],
        evidence_removed_ids=comparison["evidence_removed_ids"],
    )
    db.add(resolution)
    db.commit()
    db.refresh(resolution)
    return resolution


def list_scientific_resolutions(db: Session, investigation_id: str, limit: int = 50) -> list[ScientificResolution]:
    return list(db.scalars(select(ScientificResolution).where(
        ScientificResolution.investigation_id == investigation_id
    ).order_by(ScientificResolution.created_at.desc()).limit(limit)))
