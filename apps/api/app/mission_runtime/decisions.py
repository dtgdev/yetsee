from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mission_runtime.memory import advisory_memory_context, apply_memory_to_objective
from app.models.agent import AgentFinding
from app.models.mission import InvestigationMission, InvestigationMissionStep, ScientificDecision


def _decision_action(synthesis: dict) -> tuple[str, str, str, str]:
    contradictions = int(synthesis.get("contradiction_count") or 0)
    gaps = int(synthesis.get("evidence_gap_count") or 0)
    evidence = len(synthesis.get("evidence_ids") or [])
    agreements = int(synthesis.get("agreement_count") or 0)

    if contradictions:
        return ("resolve_agent_disagreement", "high", "Resolve the cross-agent disagreement by testing the disputed claims against independent evidence before increasing confidence.", "Resolve the detected agent disagreement: collect independent evidence for the disputed claims, inspect contradictory provenance, and re-evaluate the investigation synthesis.")
    if gaps:
        return ("collect_independent_evidence", "high" if gaps >= 2 else "medium", "Close evidence gaps before treating unsupported specialist findings as established scientific support.", "Collect independent evidence for the unsupported specialist findings, attach explicit provenance, and re-run the scientific investigation team.")
    if evidence < 2:
        return ("expand_source_diversity", "medium", "The synthesis is evidence-backed but source diversity remains too narrow for a strong scientific conclusion.", "Expand source diversity with independent observations, then re-run evidence quality, graph analysis, and cross-agent synthesis.")
    if agreements:
        return ("human_review", "medium", "The agents show evidence-backed agreement with no explicit contradictions or evidence gaps; preserve human review before advancing the investigation.", "Review the evidence-backed cross-agent consensus and decide whether the investigation is ready for the next scientific stage.")
    return ("re_evaluate_investigation", "medium", "The current synthesis does not contain enough agreement, contradiction, or evidence-gap signal to justify a stronger action.", "Re-evaluate the investigation with additional independent evidence and a fresh cross-agent synthesis.")


def _mission_findings(db: Session, mission: InvestigationMission) -> list[AgentFinding]:
    steps = list(db.scalars(select(InvestigationMissionStep).where(
        InvestigationMissionStep.mission_id == mission.id
    ).order_by(InvestigationMissionStep.sequence.asc())))
    finding_ids: list[str] = []
    for step in steps:
        for finding_id in step.finding_ids or []:
            if finding_id not in finding_ids:
                finding_ids.append(finding_id)
    if not finding_ids:
        return []
    findings = list(db.scalars(select(AgentFinding).where(AgentFinding.id.in_(finding_ids))))
    by_id = {finding.id: finding for finding in findings}
    return [by_id[finding_id] for finding_id in finding_ids if finding_id in by_id]


def _legacy_synthesis_payload(db: Session, mission: InvestigationMission, synthesis_finding: AgentFinding) -> dict:
    """Reconstruct the minimum structured synthesis from immutable persisted mission findings.

    Older Galileo missions persisted the Investigation Agent summary and all specialist
    findings, but predate the nested metadata_json.synthesis contract. This adapter derives
    counts and lineage only from those stored records; it does not invent scientific facts.
    """
    mission_findings = _mission_findings(db, mission)
    source_findings = [finding for finding in mission_findings if finding.id != synthesis_finding.id]
    if not source_findings:
        return {}

    evidence_ids: list[str] = []
    for finding in [synthesis_finding, *source_findings]:
        for evidence_id in finding.evidence_ids or []:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)

    agent_ids: list[str] = []
    for finding in source_findings:
        if finding.agent_id not in agent_ids:
            agent_ids.append(finding.agent_id)

    agreement_count = sum(1 for finding in source_findings if finding.stance == "supporting")
    contradiction_count = sum(1 for finding in source_findings if finding.stance == "contradicting")
    evidence_gap_count = sum(1 for finding in source_findings if not (finding.evidence_ids or []))
    evidence_backed_count = sum(1 for finding in source_findings if finding.evidence_ids or [])

    return {
        "agent_ids": agent_ids,
        "finding_count": len(source_findings),
        "agreement_count": agreement_count,
        "contradiction_count": contradiction_count,
        "evidence_gap_count": evidence_gap_count,
        "evidence_backed_count": evidence_backed_count,
        "evidence_ids": evidence_ids,
        "source_findings": [
            {
                "finding_id": finding.id,
                "agent_id": finding.agent_id,
                "stance": finding.stance,
                "confidence": finding.confidence,
                "evidence_ids": list(finding.evidence_ids or []),
            }
            for finding in source_findings
        ],
        "legacy_reconstructed": True,
    }


def _synthesis_finding_for_mission(db: Session, mission: InvestigationMission) -> AgentFinding | None:
    mission_findings = _mission_findings(db, mission)
    for finding in reversed(mission_findings):
        if finding.category == "investigation_synthesis":
            return finding
    return db.scalar(select(AgentFinding).where(
        AgentFinding.target_id == mission.investigation_id,
        AgentFinding.category == "investigation_synthesis",
    ).order_by(AgentFinding.created_at.desc()))


def propose_scientific_decision(db: Session, mission_id: str) -> ScientificDecision:
    mission = db.get(InvestigationMission, mission_id)
    if mission is None:
        raise KeyError("Mission not found")
    if mission.status != "completed":
        raise ValueError("Scientific decisions require a completed mission")

    finding = _synthesis_finding_for_mission(db, mission)
    if finding is None:
        raise ValueError("Completed mission has no investigation synthesis finding")

    metadata = finding.metadata_json or {}
    synthesis = metadata.get("synthesis") or _legacy_synthesis_payload(db, mission, finding)
    if not synthesis:
        raise ValueError("Investigation synthesis has no structured payload and mission findings cannot reconstruct one")
    existing = db.scalar(select(ScientificDecision).where(ScientificDecision.synthesis_finding_id == finding.id))
    if existing is not None:
        return existing

    action_type, priority, rationale, objective = _decision_action(synthesis)
    memory_context = advisory_memory_context(db, mission.investigation_id, action_type)
    objective = apply_memory_to_objective(objective, memory_context)
    contradictions = int(synthesis.get("contradiction_count") or 0)
    gaps = int(synthesis.get("evidence_gap_count") or 0)
    evidence_backed = int(synthesis.get("evidence_backed_count") or 0)
    finding_count = max(1, int(synthesis.get("finding_count") or 1))
    confidence = min(0.99, max(0.5, 0.58 + min(contradictions, 2) * 0.10 + min(gaps, 3) * 0.06 + (evidence_backed / finding_count) * 0.12))

    decision = ScientificDecision(
        investigation_id=mission.investigation_id,
        mission_id=mission.id,
        synthesis_finding_id=finding.id,
        action_type=action_type,
        status="proposed",
        priority=priority,
        confidence=round(confidence, 4),
        rationale=rationale,
        proposed_objective=objective,
        source_agent_ids=list(synthesis.get("agent_ids") or []),
        source_finding_ids=[item.get("finding_id") for item in synthesis.get("source_findings") or [] if item.get("finding_id")],
        evidence_ids=list(synthesis.get("evidence_ids") or []),
        basis_json={
            "agreement_count": int(synthesis.get("agreement_count") or 0),
            "contradiction_count": contradictions,
            "evidence_gap_count": gaps,
            "evidence_backed_count": evidence_backed,
            "finding_count": int(synthesis.get("finding_count") or 0),
            "recommendation": metadata.get("recommendation"),
            "legacy_reconstructed": bool(synthesis.get("legacy_reconstructed")),
            "memory_context": memory_context,
        },
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def create_mission_from_decision(db: Session, decision_id: str) -> InvestigationMission:
    from app.mission_runtime.engine import create_mission

    decision = db.get(ScientificDecision, decision_id)
    if decision is None:
        raise KeyError("Scientific decision not found")
    if decision.next_mission_id:
        mission = db.get(InvestigationMission, decision.next_mission_id)
        if mission is not None:
            return mission

    memory_context = (decision.basis_json or {}).get("memory_context") or {}
    mission = create_mission(
        db,
        decision.investigation_id,
        objective=decision.proposed_objective,
        requested_by="scientific_decision:human_approved",
        metadata={
            "created_from": "scientific_decision",
            "decision_id": decision.id,
            "parent_mission_id": decision.mission_id,
            "synthesis_finding_id": decision.synthesis_finding_id,
            "action_type": decision.action_type,
            "advisory_memory_ids": list(memory_context.get("memory_ids") or []),
            "memory_is_canonical_evidence": False,
        },
    )
    decision.next_mission_id = mission.id
    decision.status = "mission_created"
    db.commit()
    db.refresh(decision)
    db.refresh(mission)
    return mission


def list_scientific_decisions(db: Session, investigation_id: str, limit: int = 50) -> list[ScientificDecision]:
    return list(db.scalars(select(ScientificDecision).where(
        ScientificDecision.investigation_id == investigation_id
    ).order_by(ScientificDecision.created_at.desc()).limit(limit)))
