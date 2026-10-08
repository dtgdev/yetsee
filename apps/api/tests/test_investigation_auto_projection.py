from copy import deepcopy
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
import app.knowledge_graph.auto_projection as auto_projection
from app.db.base import Base
from app.knowledge_graph.auto_projection import ensure_investigation_projection
from app.knowledge_graph.projection import evidence_scoped_investigation_graph
from app.knowledge_graph.query import query_investigation_graph
from app.knowledge_graph.read_model import read_investigation_graph
from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.graph import InvestigationGraphProjection
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.relationship import Relationship
from app.models.scientific_literature import ScientificPassage, ScientificPublication


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _investigation(db, slug="auto-projection"):
    investigation = Investigation(title="Technology adoption", slug=slug, confidence=0.3)
    db.add(investigation)
    db.flush()
    return investigation


def _observation(db, investigation, ref="first", occurred_at="2026-01-01T00:00:00Z"):
    observation = Observation(
        source="test", source_ref=ref, topic="Technology adoption",
        metric="technology_development", value=1.0,
        observed_at=datetime(2026, 10, 5, tzinfo=timezone.utc), content_hash=ref,
        payload={
            "occurred_at": occurred_at,
            "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
            "technology": {"name": "Reasoning systems", "kind": "technology", "key": "technology:reasoning"},
            "evidence_state": {
                "type": "quality", "status": "provisional", "confidence": 0.9,
                "target": {"key": "company:exampleco"},
            },
        },
    )
    db.add(observation)
    db.flush()
    link = EvidenceLink(investigation_id=investigation.id, observation_id=observation.id,
                        stance="supporting", weight=1.0)
    db.add(link)
    db.flush()
    return observation, link


def _counts(db):
    return tuple(db.scalar(select(func.count()).select_from(model)) for model in
                 [Entity, Relationship, EvidenceLink, Observation, ScientificPassage])


def test_all_layers_prepare_once_and_readers_share_the_same_graph(db, monkeypatch):
    investigation = _investigation(db)
    observation, _ = _observation(db, investigation)
    db.commit()
    payload_before = deepcopy(observation.payload)

    prepared = ensure_investigation_projection(db, investigation.id)
    assert prepared["rebuilt"] is True
    assert set(prepared["layers"]) == {"literature", "cross_domain", "temporal", "evidence_state"}
    before = _counts(db)

    def unexpected(*args, **kwargs):
        raise AssertionError("Unchanged inputs must not run any projector")

    monkeypatch.setattr(auto_projection, "project_temporal_events", unexpected)
    assert ensure_investigation_projection(db, investigation.id)["rebuilt"] is False
    graph = read_investigation_graph(db, investigation.id)
    again = read_investigation_graph(db, investigation.id)
    path = query_investigation_graph(db, investigation.id, query_type="path",
                                    node_ref="company:exampleco", target_ref="technology:reasoning")
    filtered = evidence_scoped_investigation_graph(db, investigation.id, [observation.id])
    assert path["result_count"] == 1
    assert path["read_model"] == graph["read_model"] == filtered["read_model"]
    assert graph["nodes"] == again["nodes"] and graph["edges"] == again["edges"]
    assert graph["read_model"]["graph_id"] == again["read_model"]["graph_id"]
    assert _counts(db) == before
    assert observation.payload == payload_before
    assert investigation.confidence == 0.3
    assert not db.new and not db.dirty


def test_failure_rolls_back_all_layers_and_does_not_mark_projection_current(db, monkeypatch):
    investigation = _investigation(db)
    _observation(db, investigation)
    db.commit()
    before = _counts(db)

    def failed(*args, **kwargs):
        raise ValueError("Invalid ontology assertion")

    monkeypatch.setattr(auto_projection, "project_evidence_state_graph", failed)
    with pytest.raises(ValueError, match="Invalid ontology"):
        ensure_investigation_projection(db, investigation.id)
    assert _counts(db) == before
    assert db.get(InvestigationGraphProjection, investigation.id) is None


def test_new_evidence_and_changed_payload_refresh_projection_and_current_assessment(db):
    investigation = _investigation(db)
    first, _ = _observation(db, investigation)
    db.commit()
    old = ensure_investigation_projection(db, investigation.id)
    second, _ = _observation(db, investigation, "second", "2026-02-01T00:00:00Z")
    first.payload = {**first.payload, "evidence_state": {
        **first.payload["evidence_state"], "status": "uncertain", "confidence": 0.2,
    }}
    db.commit()
    new = ensure_investigation_projection(db, investigation.id)
    assert new["rebuilt"] is True and new["input_fingerprint"] != old["input_fingerprint"]
    graph = read_investigation_graph(db, investigation.id)
    assert graph["metrics"]["observations"] == 2
    assessments = [node for node in graph["nodes"] if node["kind"] == "assessment"]
    updated = next(node for node in assessments if
                   node["metadata"]["attributes"].get("source_observation_id") == first.id)
    assert updated["label"] == "Quality: uncertain"
    assert next(edge for edge in graph["edges"] if
                edge["source"] == updated["id"] and edge["kind"] == "ASSESSMENT_CONCERNS")["confidence"] == 0.2
    assert any(second.id in edge["evidence_ids"] for edge in graph["edges"])


def test_shared_observation_does_not_expose_other_investigation_assessments(db):
    first = _investigation(db, "first")
    second = _investigation(db, "second")
    observation, _ = _observation(db, first)
    db.add(EvidenceLink(investigation_id=second.id, observation_id=observation.id,
                        stance="contextual", weight=1.0))
    db.commit()
    ensure_investigation_projection(db, first.id)
    ensure_investigation_projection(db, second.id)
    graph = read_investigation_graph(db, first.id)
    assessments = [node for node in graph["nodes"] if node["kind"] == "assessment"]
    assert len(assessments) == 1
    assert all(node["metadata"]["attributes"]["investigation_id"] == first.id for node in assessments)


def test_detached_evidence_and_obsolete_temporal_edges_are_hidden_after_refresh(db):
    investigation = _investigation(db)
    first, _ = _observation(db, investigation)
    last, last_link = _observation(db, investigation, "last", "2026-03-01T00:00:00Z")
    db.commit()
    ensure_investigation_projection(db, investigation.id)
    middle, _ = _observation(db, investigation, "middle", "2026-02-01T00:00:00Z")
    db.commit()
    ensure_investigation_projection(db, investigation.id)
    graph = read_investigation_graph(db, investigation.id)
    order_edges = [edge for edge in graph["edges"] if edge["kind"] == "EVENT_PRECEDES"]
    assert len(order_edges) == 2
    assert all(middle.id in edge["evidence_ids"] for edge in order_edges)
    db.delete(last_link)
    db.commit()
    ensure_investigation_projection(db, investigation.id)
    graph = read_investigation_graph(db, investigation.id)
    assert graph["metrics"]["observations"] == 2
    assert all(last.id not in edge["evidence_ids"] for edge in graph["edges"])
    assert first.id in {node["domain_id"] for node in graph["nodes"]}


def test_literature_context_and_assessments_are_prepared_without_canonical_mutation(db):
    investigation = _investigation(db)
    publication = ScientificPublication(
        source_system="pubmed", source_id="12345", pmid="12345", title="Research study",
        metadata_json={"clinical_trial_ids": ["NCT12345678"]}, content_hash="publication",
    )
    db.add(publication)
    db.flush()
    passage = ScientificPassage(publication_id=publication.id, section="Abstract",
                               text="First-line osimertinib in EGFRm NSCLC using plasma sequencing.",
                               content_hash="passage", provenance_json={"canonical": True})
    db.add(passage)
    db.flush()
    db.add(EvidenceLink(investigation_id=investigation.id, scientific_passage_id=passage.id,
                        stance="supporting", weight=1.0))
    db.commit()
    original_text = passage.text
    ensure_investigation_projection(db, investigation.id)
    graph = read_investigation_graph(db, investigation.id)
    assert {"publication", "source", "clinical_trial", "assessment"} <= {
        node["kind"] for node in graph["nodes"]
    }
    assert graph["metrics"]["literature_passages"] == 1
    assert graph["metrics"]["observations"] == 0
    assert passage.text == original_text and investigation.confidence == 0.3
    counts = _counts(db)
    assert ensure_investigation_projection(db, investigation.id, force=True)["rebuilt"] is True
    assert _counts(db) == counts


def test_research_question_changes_invalidate_derived_gap_context(db):
    investigation = _investigation(db)
    db.commit()
    first = ensure_investigation_projection(db, investigation.id)
    investigation.attributes = {"research_question": "What causes technology adoption?"}
    db.commit()
    assert read_investigation_graph(db, investigation.id)["auto_projection"]["status"] == "stale"
    second = ensure_investigation_projection(db, investigation.id)
    assert second["rebuilt"] is True
    assert second["input_fingerprint"] != first["input_fingerprint"]


def test_missing_and_empty_investigations(db):
    with pytest.raises(KeyError):
        ensure_investigation_projection(db, "missing")
    investigation = _investigation(db)
    db.commit()
    ensure_investigation_projection(db, investigation.id)
    graph = read_investigation_graph(db, investigation.id)
    assert graph["metrics"]["observations"] == graph["metrics"]["literature_passages"] == 0
    assert graph["auto_projection"]["status"] == "current"


def test_fingerprint_is_stable_across_sessions_and_reader_reports_stale_inputs(db):
    investigation = _investigation(db)
    observation, _ = _observation(db, investigation)
    db.commit()
    investigation_id = investigation.id
    first = ensure_investigation_projection(db, investigation_id)
    with Session(db.get_bind(), expire_on_commit=False) as second:
        cached = ensure_investigation_projection(second, investigation_id)
        assert cached["input_fingerprint"] == first["input_fingerprint"]
        assert cached["rebuilt"] is False
    observation.payload = {**observation.payload, "new_source_context": "updated"}
    db.commit()
    counts = _counts(db)
    graph = read_investigation_graph(db, investigation_id)
    assert graph["auto_projection"]["status"] == "stale"
    assert _counts(db) == counts


def test_http_preparation_read_model_legacy_graph_filter_and_query_share_identity(db):
    from fastapi.testclient import TestClient
    from app.db.session import get_db
    from app.main import app

    investigation = _investigation(db)
    observation, _ = _observation(db, investigation)
    db.commit()
    prefix = f"/api/v1/investigations/{investigation.id}/graph"

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"{prefix}/auto-project", json={})
            assert response.status_code == 200
            assert response.json()["rebuilt"] is True
            assert client.post(f"{prefix}/auto-project", json={}).json()["rebuilt"] is False
            unified = client.get(f"{prefix}/read-model")
            legacy = client.get(prefix)
            assert unified.status_code == legacy.status_code == 200
            assert unified.json()["read_model"] == legacy.json()["read_model"]
            query = client.post(f"{prefix}/query", json={
                "query_type": "path", "node_ref": "company:exampleco",
                "target_ref": "technology:reasoning",
            })
            assert query.status_code == 200 and query.json()["result_count"] == 1
            assert query.json()["read_model"] == unified.json()["read_model"]
            scope = client.post(f"{prefix}/project", json={"evidence_ids": [observation.id]})
            assert scope.status_code == 200
            assert scope.json()["read_model"] == unified.json()["read_model"]
            assert client.post("/api/v1/investigations/missing/graph/auto-project", json={}).status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
