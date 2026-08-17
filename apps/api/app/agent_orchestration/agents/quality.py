from sqlalchemy import select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.models.agent import AgentFinding

class QualityAgent:
    def manifest(self):
        return AgentManifest("quality_agent", "1.0", "Quality Agent", "Audits traceability and guards against conclusions that are disconnected from evidence.", ("audit_traceability","audit_agent_output"), ("read:investigation","read:findings","read:evidence","write:findings"))
    def execute(self, db, context):
        inv, links, observations=investigation_bundle(db, context.target_id)
        findings=list(db.scalars(select(AgentFinding).where(AgentFinding.target_id==inv.id)))
        unattached=sum(1 for f in findings if not f.evidence_ids and f.category not in {"counter_evidence","opportunity_paths"})
        score=1.0
        if not links: score-=.5
        if unattached: score-=min(.3, unattached*.05)
        severity="info" if score>=.8 else "warning"
        draft=FindingDraft("traceability","Investigation traceability audit",f"Traceability score {score:.0%}. {len(links)} evidence link(s), {len(findings)} prior agent finding(s), {unattached} potentially unattached finding(s).",severity,"neutral",.95,[o.id for o in observations],{"traceability_score":score,"unattached_findings":unattached})
        return AgentResult(summary=f"Traceability audit completed for {inv.title}.", confidence=.95, findings=[draft], output={"traceability_score":score}, permissions_used=["read:investigation","read:findings","read:evidence","write:findings"])
