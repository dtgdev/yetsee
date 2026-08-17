from sqlalchemy import select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.models.opportunity import Opportunity

class OpportunityAnalystAgent:
    def manifest(self):
        return AgentManifest("opportunity_analyst", "1.0", "Opportunity Analyst", "Reviews possible action paths without presenting them as facts or recommendations.", ("enumerate_action_paths","audit_opportunities"), ("read:investigation","read:opportunities","write:findings"))
    def execute(self, db, context):
        inv, _, observations=investigation_bundle(db, context.target_id)
        existing=list(db.scalars(select(Opportunity).where(Opportunity.investigation_id==inv.id)))
        paths=["investment","startup","commerce"]
        finding=FindingDraft("opportunity_paths","Possible action paths",f"{len(existing)} stored opportunity hypothesis(es). Candidate lenses: {', '.join(paths)}. These are possible actions, not recommendations.","info","neutral",.7,[o.id for o in observations],{"existing":len(existing),"paths":paths})
        return AgentResult(summary=f"Reviewed opportunity surface for {inv.title}.", confidence=.7, findings=[finding], output={"existing_opportunities":len(existing),"candidate_paths":paths}, permissions_used=["read:investigation","read:opportunities","write:findings"])
