from sqlalchemy import select

from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.agent_orchestration.synthesis import synthesize_findings
from app.models.agent import AgentFinding
from app.models.mission import InvestigationMissionStep


class InvestigationAgent:
    def manifest(self):
        return AgentManifest(
            "investigation_agent",
            "1.1",
            "Investigation Agent",
            "Coordinates the living investigation and synthesizes audited specialist findings without altering canonical evidence.",
            ("synthesize_findings", "manage_investigation"),
            ("read:investigation", "read:findings", "read:evidence", "write:findings"),
        )

    def _specialist_findings(self, db, investigation_id, inputs):
        mission_id = inputs.get("mission_id")
        if mission_id:
            step_ids = list(
                db.scalars(
                    select(InvestigationMissionStep.id).where(
                        InvestigationMissionStep.mission_id == mission_id,
                        InvestigationMissionStep.agent_id != "investigation_agent",
                    )
                )
            )
            if step_ids:
                task_ids = list(
                    db.scalars(
                        select(InvestigationMissionStep.task_id).where(
                            InvestigationMissionStep.id.in_(step_ids),
                            InvestigationMissionStep.task_id.is_not(None),
                        )
                    )
                )
                if task_ids:
                    return list(
                        db.scalars(
                            select(AgentFinding)
                            .where(AgentFinding.task_id.in_(task_ids))
                            .order_by(AgentFinding.created_at.asc())
                        )
                    )

        return list(
            db.scalars(
                select(AgentFinding)
                .where(
                    AgentFinding.target_id == investigation_id,
                    AgentFinding.agent_id != "investigation_agent",
                )
                .order_by(AgentFinding.created_at.asc())
            )
        )

    def execute(self, db, context):
        inv, _, observations = investigation_bundle(db, context.target_id)
        prior = self._specialist_findings(db, inv.id, context.inputs)
        synthesis = synthesize_findings(prior)

        confidence = max(
            0.2,
            min(
                0.95,
                inv.confidence
                - min(0.25, synthesis["critical_count"] * 0.04)
                - min(0.12, synthesis["contradiction_count"] * 0.03)
                - min(0.10, synthesis["evidence_gap_count"] * 0.01)
                + min(0.08, synthesis["supporting_count"] * 0.02),
            ),
        )

        if synthesis["contradiction_count"]:
            recommendation = "resolve_agent_disagreement"
        elif synthesis["evidence_gap_count"] or synthesis["critical_count"]:
            recommendation = "collect_targeted_evidence"
        else:
            recommendation = "ready_for_reasoning"

        detail = (
            f"{synthesis['agent_count']} specialist agent(s) produced "
            f"{synthesis['finding_count']} finding(s): "
            f"{synthesis['supporting_count']} supporting, "
            f"{synthesis['critical_count']} critical, and "
            f"{synthesis['neutral_count']} neutral. "
            f"Cross-agent comparison found {synthesis['agreement_count']} shared-evidence agreement(s), "
            f"{synthesis['contradiction_count']} contradiction(s), and "
            f"{synthesis['evidence_gap_count']} finding(s) without direct evidence. "
            f"Recommended state: {recommendation}."
        )

        draft = FindingDraft(
            "cross_agent_synthesis",
            "Cross-agent scientific synthesis",
            detail,
            "warning" if synthesis["contradiction_count"] or synthesis["critical_count"] else "info",
            "neutral",
            confidence,
            synthesis["evidence_ids"],
            {
                "recommendation": recommendation,
                "mission_id": context.inputs.get("mission_id"),
                "mission_step_id": context.inputs.get("mission_step_id"),
                "synthesis": synthesis,
            },
        )
        return AgentResult(
            summary=f"Synthesized audited specialist review for {inv.title}.",
            recommendation=recommendation,
            confidence=confidence,
            findings=[draft],
            output={"synthesis": synthesis},
            permissions_used=["read:investigation", "read:findings", "read:evidence", "write:findings"],
        )
