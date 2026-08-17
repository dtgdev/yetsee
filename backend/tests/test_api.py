from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_demo_flow_and_investigation():
    r = client.post("/api/v1/discovery/demo")
    assert r.status_code == 200
    assert r.json()["opportunities"] == 3
    opportunities = client.get("/api/v1/opportunities").json()
    assert len(opportunities) >= 3
    detail = client.get(f"/api/v1/opportunities/{opportunities[0]['id']}/investigation")
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["evidence"]) == 5
    assert body["supporting_sources"] == 5


def test_runs_endpoint():
    client.post("/api/v1/discovery/demo")
    r = client.get("/api/v1/runs")
    assert r.status_code == 200
    assert len(r.json()) >= 1
