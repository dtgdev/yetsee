from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.knowledge_graph.query import query_investigation_graph
from app.knowledge_graph.temporal_events import project_temporal_events
from app.knowledge_graph.cross_domain_projection import project_cross_domain_observation_graph
from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation


def _db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def _observation(ref: str, metric: str, occurred_at: str, payload: dict, h: str) -> Observation:
    return Observation(
        source="test",
        source_ref=ref,
        topic=str(payload.get("company") or payload.get("technology") or metric),
        metric=metric,
        value=1.0,
        observed_at=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
        payload={**payload, "occurred_at": occurred_at},
        content_hash=h * 64,
    )


def test_path_query_returns_evidence_backed_cross_domain_chain():
    db = _db()
    try:
        investigation = Investigation(
            title="Technology adoption",
            slug="technology-adoption-query",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        observation = _observation(
            "tech:1",
            "technology_development",
            "2026-01-01T00:00:00Z",
            {
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "technology": {
                    "name": "Reasoning systems",
                    "kind": "technology",
                    "key": "technology:reasoning-systems",
                },
            },
            "1",
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

        result = query_investigation_graph(
            db,
            investigation.id,
            query_type="path",
            node_ref="company:exampleco",
            target_ref="technology:reasoning-systems",
        )

        assert result["result_count"] == 1
        path = result["paths"][0]
        assert path["hop_count"] == 1
        assert path["relationships"][0]["kind"] == "COMPANY_DEVELOPS_TECHNOLOGY"
        assert path["evidence_ids"] == [observation.id]
        assert path["evidence"][0]["kind"] == "observation"
        assert path["evidence"][0]["source_ref"] == "tech:1"
        assert result["policy"]["path_is_not_causality"] is True
    finally:
        db.close()


def test_why_query_finds_evidence_path_without_mutation():
    db = _db()
    try:
        investigation = Investigation(
            title="Why query",
            slug="why-query",
            status="collecting",
            confidence=0.2,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        observation = _observation(
            "launch:1",
            "product_launch",
            "2026-02-01T00:00:00Z",
            {
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "product": {"name": "Product A", "kind": "product", "key": "product:product-a"},
            },
            "2",
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
        before = investigation.confidence

        result = query_investigation_graph(
            db,
            investigation.id,
            query_type="why",
            node_ref="company:exampleco",
            limit=5,
        )

        assert result["result_count"] >= 1
        assert any(observation.id in path["evidence_ids"] for path in result["paths"])
        db.refresh(investigation)
        assert investigation.confidence == before
        assert result["policy"]["read_only"] is True
    finally:
        db.close()


def test_depends_on_query_lists_relationships_using_one_evidence_item():
    db = _db()
    try:
        investigation = Investigation(
            title="Dependency query",
            slug="dependency-query",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        observation = _observation(
            "funding:1",
            "funding_round",
            "2026-03-01T00:00:00Z",
            {
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "funding_round": {
                    "name": "ExampleCo Series A",
                    "kind": "funding_round",
                    "key": "funding-round:exampleco-series-a",
                },
            },
            "3",
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

        result = query_investigation_graph(
            db,
            investigation.id,
            query_type="depends_on",
            evidence_id=observation.id,
        )

        assert result["result_count"] >= 1
        kinds = {
            path["relationships"][0]["kind"]
            for path in result["paths"]
        }
        assert "COMPANY_RAISED_FUNDING" in kinds
        assert all(path["evidence"][0]["evidence_id"] == observation.id for path in result["paths"])
    finally:
        db.close()


def test_before_query_returns_temporal_predecessor_only():
    db = _db()
    try:
        investigation = Investigation(
            title="Temporal query",
            slug="temporal-query",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        first = _observation(
            "patent:1",
            "patent",
            "2026-01-01T00:00:00Z",
            {
                "patent": {"name": "US123", "kind": "patent", "key": "patent:us123"},
                "technology": {
                    "name": "Reasoning systems",
                    "kind": "technology",
                    "key": "technology:reasoning-systems",
                },
            },
            "4",
        )
        second = _observation(
            "funding:2",
            "funding_round",
            "2026-02-01T00:00:00Z",
            {
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "funding_round": {
                    "name": "ExampleCo Series B",
                    "kind": "funding_round",
                    "key": "funding-round:exampleco-series-b",
                },
            },
            "5",
        )
        db.add_all([first, second])
        db.flush()
        for observation in (first, second):
            db.add(EvidenceLink(
                investigation_id=investigation.id,
                observation_id=observation.id,
                stance="supporting",
                weight=1.0,
            ))
        db.commit()

        temporal = project_temporal_events(db, investigation.id)
        later_event = temporal["timeline"][1]

        result = query_investigation_graph(
            db,
            investigation.id,
            query_type="before",
            node_ref=later_event["event_id"],
        )

        assert result["result_count"] == 1
        relationship = result["paths"][0]["relationships"][0]
        assert relationship["kind"] == "EVENT_PRECEDES"
        assert result["policy"]["temporal_precedence_is_not_causality"] is True
    finally:
        db.close()


def test_query_rejects_ambiguous_or_missing_inputs():
    db = _db()
    try:
        investigation = Investigation(
            title="Validation",
            slug="query-validation",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.commit()

        try:
            query_investigation_graph(db, investigation.id, query_type="path", node_ref="x")
            assert False, "path query should require target_ref"
        except (KeyError, ValueError):
            pass

        try:
            query_investigation_graph(db, investigation.id, query_type="unknown")
            assert False, "unknown query_type should fail"
        except ValueError as exc:
            assert "query_type must be one of" in str(exc)
    finally:
        db.close()
