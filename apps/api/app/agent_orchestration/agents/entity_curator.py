from sqlalchemy import select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.models.entity import Entity
from app.agent_orchestration.agents.common import UUID_RE

class EntityCuratorAgent:
    def manifest(self):
        return AgentManifest("entity_curator", "1.0", "Entity Curator", "Flags unresolved aliases, UUID-like entities and suspicious graph classifications for review.", ("audit_entities","propose_resolution"), ("read:entities","write:findings","propose:entity_merge"))
    def execute(self, db, context):
        findings=[]
        entities=list(db.scalars(select(Entity)))
        for entity in entities:
            if UUID_RE.match(entity.canonical_name):
                findings.append(FindingDraft("entity_resolution", "UUID-like graph entity needs review", f"{entity.canonical_name} appears to be an identifier rather than a canonical entity.", "warning", "critical", .99, metadata={"entity_id":entity.id}))
            if entity.canonical_name.lower() in {"demo","unknown","none","null"}:
                findings.append(FindingDraft("entity_quality", f"Generic entity: {entity.canonical_name}", "Generic infrastructure/source labels should not become high-value semantic entities without explicit classification.", "warning", "critical", .92, metadata={"entity_id":entity.id}))
        return AgentResult(summary=f"Reviewed {len(entities)} entities; flagged {len(findings)} for curation.", confidence=.95, findings=findings, output={"entities_reviewed":len(entities),"flags":len(findings)}, permissions_used=["read:entities","write:findings"])
