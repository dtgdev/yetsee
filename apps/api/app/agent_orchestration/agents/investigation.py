from sqlalchemy import select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.models.agent import AgentFinding

class InvestigationAgent:
    def manifest(self):
        return AgentManifest("investigation_agent", "1.0", "Investigation Agent", "Coordinates the living investigation and synthesizes audited specialist findings without altering canonical evidence.", ("synthesize_findings","manage_investigation"), ("read:investigation","read:findings","read:evidence","write:findings"))
    def execute(self, db, context):
        inv, _, observations=investigation_bundle(db, context.target_id)
        prior=list(db.scalars(select(AgentFinding).where(AgentFinding.target_id==inv.id).order_by(AgentFinding.created_at)))
        critical=[f for f in prior if f.stance=="critical"]
        supporting=[f for f in prior if f.stance=="supporting"]
        confidence=max(.2, min(.95, inv.confidence - min(.25,len(critical)*.04) + min(.08,len(supporting)*.02)))
        recommendation="continue_monitoring" if critical else "ready_for_reasoning"
        draft=FindingDraft("investigation_synthesis","Agent team synthesis",f"Specialists produced {len(prior)} finding(s): {len(supporting)} supporting and {len(critical)} critical. Recommended state: {recommendation}.","info","neutral",confidence,[o.id for o in observations],{"recommendation":recommendation,"supporting":len(supporting),"critical":len(critical)})
        return AgentResult(summary=f"Synthesized specialist review for {inv.title}.", recommendation=recommendation, confidence=confidence, findings=[draft], output={"supporting_findings":len(supporting),"critical_findings":len(critical)}, permissions_used=["read:investigation","read:findings","read:evidence","write:findings"])
