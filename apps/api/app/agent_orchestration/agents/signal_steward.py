from sqlalchemy import func, select
from app.agent_orchestration.contracts import AgentManifest, AgentResult, FindingDraft
from app.models.connector import ConnectorRun, ConnectorState
from app.models.observation import Observation

class SignalStewardAgent:
    def manifest(self):
        return AgentManifest("signal_steward", "1.0", "Signal Steward", "Audits connector health, ingestion gaps and source quality without changing observations.", ("audit_connectors","detect_ingestion_gaps"), ("read:observations","read:connector_state","write:findings"))
    def execute(self, db, context):
        findings=[]
        states=list(db.scalars(select(ConnectorState)))
        obs=db.scalar(select(func.count()).select_from(Observation)) or 0
        for state in states:
            if state.consecutive_failures:
                findings.append(FindingDraft("connector_health", f"{state.connector_id} has repeated failures", f"Connector has {state.consecutive_failures} consecutive failure(s).", "warning", "critical", .95))
        return AgentResult(summary=f"Audited {len(states)} connector state(s) and {obs} observations.", confidence=.95, findings=findings, output={"connectors":len(states),"observations":obs}, permissions_used=["read:observations","read:connector_state","write:findings"])
