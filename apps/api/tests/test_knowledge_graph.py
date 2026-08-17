from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401 - register all mappings
from app.db.base import Base
from app.knowledge_graph.engine import neighborhood, rebuild_graph
from app.knowledge_graph.resolver import resolve_phrase
from app.models.entity import Entity
from app.models.feature import Feature
from app.models.observation import Observation
from app.models.relationship import Relationship


def test_entity_resolution_handles_aliases():
    assert resolve_phrase("social running").canonical_key == "running clubs"
    assert resolve_phrase("NVDA").canonical_name == "NVIDIA"
    assert resolve_phrase("agentic ai").canonical_key == "ai agents"


def test_graph_is_evidence_backed_and_emits_graph_features():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        observations = [
            Observation(
                source="reddit",
                source_ref="1",
                topic="running clubs",
                metric="community_velocity",
                value=0.7,
                observed_at=now - timedelta(hours=2),
                payload={"title": "Running clubs and social running"},
                content_hash="a" * 64,
            ),
            Observation(
                source="news",
                source_ref="2",
                topic="AI agents",
                metric="mentions",
                value=0.8,
                observed_at=now - timedelta(hours=1),
                payload={"title": "NVIDIA and OpenAI expand AI agents infrastructure"},
                content_hash="b" * 64,
            ),
        ]
        db.add_all(observations)
        db.flush()
        db.add_all([
            Feature(
                subject="running clubs", feature_type="semantic", name="embedding", value=None,
                vector=[1.0, 0.0], window="30d", extractor_id="semantic_fingerprint",
                extractor_version="1.0", confidence=1.0, evidence_ids=[observations[0].id],
                attributes={}, computed_at=now,
            ),
            Feature(
                subject="ai agents", feature_type="semantic", name="embedding", value=None,
                vector=[0.95, 0.05], window="30d", extractor_id="semantic_fingerprint",
                extractor_version="1.0", confidence=1.0, evidence_ids=[observations[1].id],
                attributes={}, computed_at=now,
            ),
        ])
        db.commit()
        result = rebuild_graph(db, hours=24)
        assert result["status"] == "succeeded"
        assert result["entities"] >= 6
        assert result["relationships"] >= 4
        edges = list(db.scalars(select(Relationship)))
        assert all(edge.evidence_ids for edge in edges)
        nvidia = db.scalar(select(Entity).where(Entity.canonical_key == "nvidia"))
        assert nvidia is not None
        graph = neighborhood(db, nvidia.id)
        assert graph["relationships"]
        graph_features = list(db.scalars(select(Feature).where(Feature.feature_type == "graph")))
        assert {item.name for item in graph_features} >= {"degree", "degree_centrality", "community"}
