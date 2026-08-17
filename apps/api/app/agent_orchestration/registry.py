from app.agent_orchestration.agents.discovery_analyst import DiscoveryAnalystAgent
from app.agent_orchestration.agents.entity_curator import EntityCuratorAgent
from app.agent_orchestration.agents.evidence_critic import EvidenceCriticAgent
from app.agent_orchestration.agents.evidence_agent import EvidenceAgent
from app.agent_orchestration.agents.graph_analyst import GraphAnalystAgent
from app.agent_orchestration.agents.investigation import InvestigationAgent
from app.agent_orchestration.agents.opportunity_analyst import OpportunityAnalystAgent
from app.agent_orchestration.agents.quality import QualityAgent
from app.agent_orchestration.agents.signal_steward import SignalStewardAgent
from app.agent_orchestration.agents.semantic_curator import SemanticCuratorAgent


class AgentRegistry:
    def __init__(self) -> None:
        agents = [
            SignalStewardAgent(), SemanticCuratorAgent(), EntityCuratorAgent(), DiscoveryAnalystAgent(),
            EvidenceAgent(), EvidenceCriticAgent(), GraphAnalystAgent(), OpportunityAnalystAgent(),
            QualityAgent(), InvestigationAgent(),
        ]
        self._agents = {agent.manifest().id: agent for agent in agents}

    def all(self):
        return list(self._agents.values())

    def get(self, agent_id: str):
        if agent_id not in self._agents:
            raise KeyError(agent_id)
        return self._agents[agent_id]


registry = AgentRegistry()
