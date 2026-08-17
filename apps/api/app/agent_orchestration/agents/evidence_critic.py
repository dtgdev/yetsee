from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle

class EvidenceCriticAgent:
    def manifest(self):
        return AgentManifest("evidence_critic", "1.0", "Evidence Critic", "Challenges investigations by checking evidence volume, diversity and missing counter-evidence.", ("challenge_hypothesis","find_weaknesses"), ("read:investigation","read:evidence","write:findings"))
    def execute(self, db, context):
        inv, links, observations=investigation_bundle(db, context.target_id)
        sources={o.source for o in observations}; findings=[]
        if len(observations)<3:
            findings.append(FindingDraft("evidence_strength","Thin evidence base",f"Only {len(observations)} observation(s) currently support this investigation.","warning","critical",.95,[o.id for o in observations]))
        if len(sources)<2:
            findings.append(FindingDraft("source_diversity","Low source diversity",f"Evidence currently comes from {len(sources)} distinct source(s).", "warning","critical",.9,[o.id for o in observations]))
        counter=sum(1 for link in links if link.stance in {"counter","contradicting"})
        if counter==0:
            findings.append(FindingDraft("counter_evidence","No explicit counter-evidence yet","The investigation has no counter-evidence link. Treat confidence as provisional until the thesis is actively challenged.","warning","critical",.88))
        return AgentResult(summary=f"Critiqued {inv.title}: {len(findings)} weakness(es) surfaced.", confidence=.9, findings=findings, output={"evidence":len(observations),"sources":len(sources),"counter_evidence":counter}, permissions_used=["read:investigation","read:evidence","write:findings"])
