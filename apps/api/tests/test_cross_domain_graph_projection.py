from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.knowledge_graph.cross_domain_projection import project_cross_domain_observation_graph
from app.knowledge_graph.investigation import investigation_graph
from app.models.entity import Entity
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation
from app.models.relationship import Relationship


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_cross_domain_projection_materializes_business_and_technology_objects():
    db = _db()
    try:
        investigation = Investigation(
            title="Business and technology signals",
            slug="business-technology-signals",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        observation = Observation(
            source="news",
            source_ref="news:openai-model-launch",
            topic="OpenAI",
            metric="product_launch",
            value=1.0,
            observed_at=datetime.now(timezone.utc),
            payload={
                "graph_assertions": [
                    {
                        "subject": {
                            "kind": "company",
                            "name": "OpenAI",
                            "key": "company:openai",
                        },
                        "predicate": "COMPANY_LAUNCHED_PRODUCT",
                        "object": {
                            "kind": "product",
                            "name": "Research Product",
                            "key": "product:research-product",
                        },
                        "confidence": 0.96,
                    },
                    {
                        "subject": {
                            "kind": "company",
                            "name": "OpenAI",
                            "key": "company:openai",
                        },
                        "predicate": "COMPANY_DEVELOPS_TECHNOLOGY",
                        "object": {
                            "kind": "technology",
                            "name": "Reasoning systems",
                            "key": "technology:reasoning-systems",
                        },
                        "confidence": 0.92,
                    },
                ]
            },
            content_hash="a" * 64,
        )
        db.add(observation)
        db.flush()
        db.add(EvidenceLink(
            investigation_id=investigation.id,
            observation_id=observation.id,
            stance="supporting",
            weight=1.0,
        ))
        db.commit()

        result = project_cross_domain_observation_graph(db, investigation.id)

        assert result["observation_count"] == 1
        assert result["assertion_count"] == 2
        assert result["node_count"] == 3
        assert result["relationship_count"] == 2
        assert result["policy"]["free_text_inference_disabled"] is True

        kinds = {entity.kind for entity in db.scalars(select(Entity))}
        assert {"company", "product", "technology"} <= kinds

        relationships = list(db.scalars(select(Relationship)))
        assert {item.kind for item in relationships} == {
            "COMPANY_LAUNCHED_PRODUCT",
            "COMPANY_DEVELOPS_TECHNOLOGY",
        }
        assert all(item.evidence_ids == [observation.id] for item in relationships)
        assert all(item.provenance["canonical_evidence_kind"] == "observation" for item in relationships)
        assert all(item.provenance["cross_domain_projection"] is True for item in relationships)

        graph = investigation_graph(db, investigation.id)
        graph_kinds = {node["kind"] for node in graph["nodes"]}
        assert {"company", "product", "technology"} <= graph_kinds
        graph_edge_kinds = {edge["kind"] for edge in graph["edges"]}
        assert "COMPANY_LAUNCHED_PRODUCT" in graph_edge_kinds
        assert "COMPANY_DEVELOPS_TECHNOLOGY" in graph_edge_kinds
    finally:
        db.close()


def test_cross_domain_projection_is_idempotent_and_preserves_observation_evidence():
    db = _db()
    try:
        investigation = Investigation(
            title="Funding signal",
            slug="funding-signal",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()
        observation = Observation(
            source="funding",
            source_ref="funding:example-series-a",
            topic="ExampleCo",
            metric="funding_round",
            value=1.0,
            observed_at=datetime.now(timezone.utc),
            payload={
                "graph_assertions": [
                    {
                        "subject": {
                            "kind": "company",
                            "name": "ExampleCo",
                            "key": "company:exampleco",
                        },
                        "predicate": "COMPANY_RAISED_FUNDING",
                        "object": {
                            "kind": "funding_round",
                            "name": "ExampleCo Series A",
                            "key": "funding-round:exampleco-series-a",
                        },
                    }
                ]
            },
            content_hash="b" * 64,
        )
        db.add(observation)
        db.flush()
        db.add(EvidenceLink(
            investigation_id=investigation.id,
            observation_id=observation.id,
            stance="supporting",
            weight=1.0,
        ))
        db.commit()

        first = project_cross_domain_observation_graph(db, investigation.id)
        entity_count = len(list(db.scalars(select(Entity))))
        relationship_count = len(list(db.scalars(select(Relationship))))
        second = project_cross_domain_observation_graph(db, investigation.id)

        assert first["node_count"] == second["node_count"]
        assert first["relationship_count"] == second["relationship_count"]
        assert len(list(db.scalars(select(Entity)))) == entity_count
        assert len(list(db.scalars(select(Relationship)))) == relationship_count
        assert db.get(Observation, observation.id) is not None
        assert db.get(Observation, observation.id).payload["graph_assertions"]
    finally:
        db.close()


def test_cross_domain_projection_rejects_invalid_ontology_assertion():
    db = _db()
    try:
        investigation = Investigation(
            title="Invalid assertion",
            slug="invalid-assertion",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()
        observation = Observation(
            source="news",
            source_ref="news:invalid",
            topic="Invalid",
            metric="event",
            value=1.0,
            observed_at=datetime.now(timezone.utc),
            payload={
                "graph_assertions": [
                    {
                        "subject": {"kind": "market", "name": "AI", "key": "market:ai"},
                        "predicate": "COMPANY_LAUNCHED_PRODUCT",
                        "object": {"kind": "product", "name": "Thing", "key": "product:thing"},
                    }
                ]
            },
            content_hash="c" * 64,
        )
        db.add(observation)
        db.flush()
        db.add(EvidenceLink(
            investigation_id=investigation.id,
            observation_id=observation.id,
            stance="supporting",
            weight=1.0,
        ))
        db.commit()

        try:
            project_cross_domain_observation_graph(db, investigation.id)
            assert False, "expected ontology endpoint validation to fail"
        except ValueError as exc:
            assert "Ontology endpoint mismatch" in str(exc)
    finally:
        db.close()
