from sqlalchemy import or_, select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.agent_orchestration.agents.common import investigation_bundle
from app.models.entity import Entity
from app.models.relationship import Relationship

class GraphAnalystAgent:
    def manifest(self):
        return AgentManifest("graph_analyst", "1.0", "Graph Analyst", "Examines investigation neighborhoods, bridge entities and relationship evidence.", ("inspect_neighborhood","detect_graph_risk"), ("read:graph","read:investigation","write:findings"))
    def execute(self, db, context):
        inv, _, observations=investigation_bundle(db, context.target_id)
        key=inv.title.lower().strip()
        entities=list(db.scalars(select(Entity).where((Entity.canonical_key==key) | (Entity.canonical_name.ilike(inv.title)))))
        findings=[]; edge_count=0
        for entity in entities:
            edges=list(db.scalars(select(Relationship).where(or_(Relationship.source_entity_id==entity.id, Relationship.target_entity_id==entity.id))))
            edge_count+=len(edges)
            low=[e for e in edges if e.confidence<.6]
            findings.append(FindingDraft("graph_neighborhood",f"Graph neighborhood: {entity.canonical_name}",f"Entity has {len(edges)} relationship(s); {len(low)} are below 60% confidence.","info","supporting",.82,list(dict.fromkeys(eid for e in edges for eid in e.evidence_ids))[:100],{"entity_id":entity.id,"edges":len(edges),"low_confidence_edges":len(low)}))
        if not entities:
            findings.append(FindingDraft("graph_resolution","Investigation not resolved into graph","No canonical entity matched this investigation title; graph reasoning is incomplete.","warning","critical",.9,[o.id for o in observations]))
        return AgentResult(summary=f"Graph analysis found {len(entities)} matching entity node(s) and {edge_count} edge(s).", confidence=.82, findings=findings, output={"entities":len(entities),"edges":edge_count}, permissions_used=["read:graph","read:investigation","write:findings"])
