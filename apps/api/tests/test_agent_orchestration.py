from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.agent_orchestration.engine import run_agent, run_investigation_team
from app.agent_orchestration.registry import registry
from app.db.base import Base
from app.models.agent import AgentFinding, AgentRun, AgentTask
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation


def test_agent_registry_has_stable_roles_and_permissions():
    manifests = {agent.manifest().id: agent.manifest() for agent in registry.all()}
    assert {"signal_steward", "entity_curator", "discovery_analyst", "evidence_critic", "graph_analyst", "opportunity_analyst", "quality_agent", "investigation_agent"} <= set(manifests)
    assert "write:findings" in manifests["evidence_critic"].permissions
    assert all("write:observations" not in manifest.permissions for manifest in manifests.values())


def test_investigation_team_creates_audited_tasks_and_findings():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        observation = Observation(
            source="reddit", source_ref="1", topic="running clubs", metric="community_velocity",
            value=0.8, observed_at=now, payload={"title": "Running clubs"}, content_hash="a" * 64,
        )
        investigation = Investigation(
            title="Running Clubs", slug="running-clubs", status="emerging", confidence=.82,
            summary="Community-led running is expanding.", hypothesis="May be a durable behavior shift.",
            counter_thesis="Could be seasonal.", attributes={},
        )
        db.add_all([observation, investigation]); db.flush()
        db.add(EvidenceLink(investigation_id=investigation.id, observation_id=observation.id, stance="supporting", weight=1.0))
        db.commit()

        result = run_investigation_team(db, investigation.id)
        assert len(result["tasks"]) == 6
        tasks = list(db.scalars(select(AgentTask)))
        runs = list(db.scalars(select(AgentRun)))
        findings = list(db.scalars(select(AgentFinding)))
        assert all(task.status == "completed" for task in tasks)
        assert len(runs) == len(tasks)
        assert findings
        assert any(f.category == "counter_evidence" for f in findings)
        assert any(f.category == "investigation_synthesis" for f in findings)
        assert all(run.permissions_used for run in runs)


def test_entity_curator_flags_uuid_like_entities():
    from app.models.entity import Entity
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Entity(kind="topic", canonical_name="ac81c088-4558-4a6c-acf0-8ad453b7eccc", canonical_key="ac81c088-4558-4a6c-acf0-8ad453b7eccc", aliases=[], attributes={}))
        db.commit()
        task = run_agent(db, agent_id="entity_curator", task_type="AUDIT_ENTITIES")
        findings = list(db.scalars(select(AgentFinding).where(AgentFinding.task_id == task.id)))
        assert any(f.category == "entity_resolution" for f in findings)
