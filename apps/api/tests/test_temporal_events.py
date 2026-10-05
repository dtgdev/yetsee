from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.knowledge_graph.investigation import investigation_graph
from app.knowledge_graph.temporal_events import normalize_observation_event, project_temporal_events
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


def _obs(ref: str, metric: str, occurred_at: str, payload: dict, h: str) -> Observation:
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


def test_normalizer_prefers_event_time_over_observation_time():
    observation = _obs(
        "funding:1",
        "funding_round",
        "2026-09-01T15:30:00Z",
        {
            "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
            "funding_round": {
                "name": "ExampleCo Series A",
                "kind": "funding_round",
                "key": "funding-round:exampleco-series-a",
            },
        },
        "1",
    )

    event = normalize_observation_event(observation)

    assert event is not None
    assert event["event_type"] == "funding_round"
    assert event["occurred_at"].isoformat() == "2026-09-01T15:30:00+00:00"
    assert event["time_precision"] == "timestamp"
    assert event["occurred_at"] != observation.observed_at


def test_temporal_projection_creates_event_nodes_and_order_without_causality():
    db = _db()
    try:
        investigation = Investigation(
            title="Technology sequence",
            slug="technology-sequence",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        first = _obs(
            "patent:1",
            "patent",
            "2026-01-15",
            {
                "patent": {"name": "US123", "kind": "patent", "key": "patent:us123"},
                "technology": {
                    "name": "Reasoning systems",
                    "kind": "technology",
                    "key": "technology:reasoning-systems",
                },
            },
            "2",
        )
        second = _obs(
            "funding:2",
            "funding_round",
            "2026-03-01T10:00:00Z",
            {
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "funding_round": {
                    "name": "ExampleCo Series B",
                    "kind": "funding_round",
                    "key": "funding-round:exampleco-series-b",
                },
            },
            "3",
        )
        third = _obs(
            "job:3",
            "job_posting",
            "2026-04-01T09:00:00Z",
            {
                "company": {"name": "ExampleCo", "kind": "company", "key": "company:exampleco"},
                "job_posting": {
                    "name": "Senior AI Engineer",
                    "kind": "job_posting",
                    "key": "job-posting:exampleco-ai-engineer",
                },
            },
            "4",
        )
        db.add_all([first, second, third])
        db.flush()
        for observation in (first, second, third):
            db.add(EvidenceLink(
                investigation_id=investigation.id,
                observation_id=observation.id,
                stance="supporting",
                weight=1.0,
            ))
        db.commit()

        result = project_temporal_events(db, investigation.id)

        assert result["normalized_event_count"] == 3
        assert result["precedence_relationship_count"] == 2
        assert [item["event_type"] for item in result["timeline"]] == [
            "patent",
            "funding_round",
            "job_posting",
        ]
        assert result["policy"]["temporal_order_does_not_imply_causality"] is True

        events = list(db.scalars(select(Entity).where(Entity.kind == "event")))
        assert len(events) == 3
        edges = list(db.scalars(select(Relationship)))
        precedence = [edge for edge in edges if edge.kind == "EVENT_PRECEDES"]
        assert len(precedence) == 2
        assert all(edge.provenance["causality_inferred"] is False for edge in precedence)
        assert all(edge.provenance["temporal_order_only"] is True for edge in precedence)

        graph = investigation_graph(db, investigation.id)
        graph_kinds = {node["kind"] for node in graph["nodes"]}
        assert "event" in graph_kinds
        graph_edge_kinds = {edge["kind"] for edge in graph["edges"]}
        assert "EVENT_INVOLVES" in graph_edge_kinds
        assert "EVENT_PRECEDES" in graph_edge_kinds
    finally:
        db.close()


def test_equal_timestamps_are_not_ordered():
    db = _db()
    try:
        investigation = Investigation(
            title="Same time",
            slug="same-time",
            status="collecting",
            confidence=0.0,
            attributes={},
        )
        db.add(investigation)
        db.flush()

        a = _obs(
            "launch:a",
            "product_launch",
            "2026-05-01T12:00:00Z",
            {
                "company": {"name": "A", "kind": "company", "key": "company:a"},
                "product": {"name": "Product A", "kind": "product", "key": "product:a"},
            },
            "5",
        )
        b = _obs(
            "launch:b",
            "product_launch",
            "2026-05-01T12:00:00Z",
            {
                "company": {"name": "B", "kind": "company", "key": "company:b"},
                "product": {"name": "Product B", "kind": "product", "key": "product:b"},
            },
            "6",
        )
        db.add_all([a, b])
        db.flush()
        for observation in (a, b):
            db.add(EvidenceLink(
                investigation_id=investigation.id,
                observation_id=observation.id,
                stance="supporting",
                weight=1.0,
            ))
        db.commit()

        result = project_temporal_events(db, investigation.id)

        assert result["normalized_event_count"] == 2
        assert result["precedence_relationship_count"] == 0
        assert list(db.scalars(select(Relationship).where(Relationship.kind == "EVENT_PRECEDES"))) == []
    finally:
        db.close()


def test_unstructured_text_does_not_create_temporal_event():
    observation = Observation(
        source="news",
        source_ref="news:free-text",
        topic="ExampleCo",
        metric="coverage",
        value=1.0,
        observed_at=datetime.now(timezone.utc),
        payload={"title": "ExampleCo raised funding before hiring engineers"},
        content_hash="7" * 64,
    )

    assert normalize_observation_event(observation) is None
