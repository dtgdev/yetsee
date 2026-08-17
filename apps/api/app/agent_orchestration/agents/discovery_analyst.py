from sqlalchemy import select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.models.discovery import DiscoveryCandidate

class DiscoveryAnalystAgent:
    def manifest(self):
        return AgentManifest("discovery_analyst", "1.0", "Discovery Analyst", "Reviews ensemble candidates for detector agreement and evidence strength.", ("review_candidates","recommend_promotion"), ("read:candidates","read:evidence","write:findings"))
    def execute(self, db, context):
        statement=select(DiscoveryCandidate).order_by(DiscoveryCandidate.score.desc()).limit(100)
        if context.target_id:
            statement=select(DiscoveryCandidate).where(DiscoveryCandidate.id==context.target_id)
        candidates=list(db.scalars(statement)); findings=[]
        for c in candidates:
            recommendation="promote" if c.detector_count>=2 and c.evidence_count>=2 and c.score>=.55 else "watch"
            findings.append(FindingDraft("candidate_review", f"{c.title}: {recommendation}", f"Score {c.score:.2f}, {c.detector_count} detector(s), {c.evidence_count} evidence item(s).", "info", "supporting" if recommendation=="promote" else "neutral", min(.95,max(.5,c.confidence)), c.evidence_ids, {"candidate_id":c.id,"recommendation":recommendation}))
        return AgentResult(summary=f"Reviewed {len(candidates)} discovery candidate(s).", confidence=.85, findings=findings, output={"reviewed":len(candidates)}, permissions_used=["read:candidates","read:evidence","write:findings"])
