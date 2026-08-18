from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.investigation import Investigation
from app.models.kernel import KernelCommandLog


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), factory


def seed_investigation(factory: sessionmaker) -> str:
    with factory() as db:
        investigation = Investigation(
            title="Running Clubs",
            slug="running-clubs-mission-api",
            status="collecting",
            confidence=0.5,
            attributes={},
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        return investigation.id


def test_mission_api_create_list_read_and_run():
    client, factory = make_client()
    investigation_id = seed_investigation(factory)
    try:
        created = client.post(
            f"/api/v1/investigations/{investigation_id}/missions",
            json={
                "objective": "Determine whether running clubs are durable.",
                "plan": [
                    {
                        "agent_id": "evidence_agent",
                        "task_type": "REVIEW_INVESTIGATION",
                        "inputs": {"source": "api-test"},
                    }
                ],
            },
        )
        assert created.status_code == 200
        mission = created.json()
        mission_id = mission["id"]
        assert mission["status"] == "pending"

        listed = client.get(f"/api/v1/investigations/{investigation_id}/missions")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [mission_id]

        detail = client.get(f"/api/v1/missions/{mission_id}")
        assert detail.status_code == 200
        assert detail.json()["mission"]["id"] == mission_id
        assert len(detail.json()["steps"]) == 1

        executed = client.post(f"/api/v1/missions/{mission_id}/run")
        assert executed.status_code == 200
        body = executed.json()
        assert body["mission"]["status"] == "completed"
        assert body["steps"][0]["status"] == "completed"
        assert body["steps"][0]["task_id"]
        assert body["steps"][0]["command_id"]

        with factory() as db:
            command_types = set(db.scalars(select(KernelCommandLog.command_type)))
            assert "CreateInvestigationMission" in command_types
            assert "RunInvestigationMission" in command_types
            assert "RunInvestigationAgent" in command_types
    finally:
        app.dependency_overrides.clear()


def test_mission_api_returns_not_found_for_missing_resources():
    client, _factory = make_client()
    try:
        missing_investigation = client.get("/api/v1/investigations/missing/missions")
        assert missing_investigation.status_code == 404

        missing_mission = client.get("/api/v1/missions/missing")
        assert missing_mission.status_code == 404

        missing_run = client.post("/api/v1/missions/missing/run")
        assert missing_run.status_code == 404
    finally:
        app.dependency_overrides.clear()
