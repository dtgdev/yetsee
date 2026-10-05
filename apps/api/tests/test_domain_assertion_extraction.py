from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.knowledge_graph.cross_domain_projection import project_cross_domain_observation_graph
from app.knowledge_graph.domain_assertion_extraction import extract_graph_assertions
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


def _observation(*, metric: str, payload: dict, content_hash: str) -> Observation:
    return Observation(
        source="test",
        source_ref=f"test:{content_hash[:4]}",
        topic=str(payload.get("company") or payload.get("technology") or "test"),
        metric=metric,
        value=1.0,
        observed_at=datetime.now(timezone.utc),
        payload=payload,
        content_hash=content_hash,
    )


def test_extracts_structured_product_launch_assertion():
    observation = _observation(
        metric="product_launch",
        payload={
            "company": {"name": "OpenAI", "kind": "company", "key": "company:openai"},
            "product": {"name": "Research Product", "kind": "product", "key": "product:research-product"},
            "confidence": 0.94,
        },
        content_hash="1" * 64,
    )

    assertions = extract_graph_assertions(observation)

    assert len(assertions) == 1
    assertion = assertions[0]
    assert assertion["predicate"] == "COMPANY_LAUNCHED_PRODUCT"
    assert assertion["subject"]["kind"] == "company"
    assert assertion["object"]["kind"] == "product"
    assert assertion["confidence"] == 0.94
    assert assertion["provenance"]["domain"] == "business"
    assert assertion["provenance"]["free_text_inference"] is False


def test_extracts_funding_and_patent_assertions_from_domain_events():
    funding = _observation(
        metric="coverage",
        payload={
            "domain_event": {
                "type": "funding_round",
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "funding_round": {
                    "name": "ExampleCo Series B",
                    "kind": "funding_round",
                    "key": "funding-round:exampleco-series-b",
                },
            }
        },
        content_hash="2" * 64,
    )
    patent = _observation(
        metric="coverage",
        payload={
            "domain_event": {
                "type": "patent",
                "patent": {"name": "US123", "kind": "patent", "key": "patent:us123"},
                "technology": {
                    "name": "Reasoning systems",
                    "kind": "technology",
                    "key": "technology:reasoning-systems",
                },
            }
        },
        content_hash="3" * 64,
    )

    assert extract_graph_assertions(funding)[0]["predicate"] == "COMPANY_RAISED_FUNDING"
    assert extract_graph_assertions(patent)[0]["predicate"] == "PATENT_COVERS_TECHNOLOGY"


def test_does_not_infer_from_unstructured_free_text():
    observation = _observation(
        metric="coverage",
        payload={
            "title": "OpenAI launched a new product and raised a funding round",
            "text": "NVIDIA invested in OpenAI.",
        },
        content_hash="4" * 64,
    )

    assert extract_graph_assertions(observation) == []


def test_missing_required_structured_role_produces_no_assertion():
    observation = _observation(
        metric="product_launch",
        payload={"company": "OpenAI"},
        content_hash="5" * 64,
    )

    assert extract_graph_assertions(observation) == []


def test_projection_automatically_uses_domain_aware_extraction():
    db = _db()
    try:
        investigation = Investigation(
            title="Automatic cross-domain extraction",
            slug="automatic-cross-domain-extraction",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        observation = _observation(
            metric="technology_development",
            payload={
                "company": {"name": "OpenAI", "kind": "company", "key": "company:openai"},
                "technology": {
                    "name": "Reasoning systems",
                    "kind": "technology",
                    "key": "technology:reasoning-systems",
                },
            },
            content_hash="6" * 64,
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

        assert result["assertion_count"] == 1
        assert result["policy"]["domain_aware_extraction_enabled"] is True
        assert result["policy"]["explicit_graph_assertions_take_precedence"] is True

        entities = list(db.scalars(select(Entity)))
        assert {entity.kind for entity in entities} == {"company", "technology"}

        relationships = list(db.scalars(select(Relationship)))
        assert len(relationships) == 1
        assert relationships[0].kind == "COMPANY_DEVELOPS_TECHNOLOGY"
        assert relationships[0].provenance["method"] == "domain-graph-assertion-v1"
        assert relationships[0].provenance["canonical_evidence_kind"] == "observation"
    finally:
        db.close()


def test_explicit_graph_assertions_take_precedence_over_extractor():
    db = _db()
    try:
        investigation = Investigation(
            title="Explicit assertion precedence",
            slug="explicit-assertion-precedence",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        observation = _observation(
            metric="product_launch",
            payload={
                "company": {"name": "OpenAI", "kind": "company", "key": "company:openai"},
                "product": {"name": "Auto Product", "kind": "product", "key": "product:auto-product"},
                "graph_assertions": [
                    {
                        "subject": {"kind": "company", "name": "OpenAI", "key": "company:openai"},
                        "predicate": "COMPANY_DEVELOPS_TECHNOLOGY",
                        "object": {
                            "kind": "technology",
                            "name": "Explicit Technology",
                            "key": "technology:explicit-technology",
                        },
                    }
                ],
            },
            content_hash="7" * 64,
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

        project_cross_domain_observation_graph(db, investigation.id)
        relationship = db.scalar(select(Relationship))

        assert relationship is not None
        assert relationship.kind == "COMPANY_DEVELOPS_TECHNOLOGY"
        product = db.scalar(select(Entity).where(Entity.kind == "product"))
        assert product is None
    finally:
        db.close()
