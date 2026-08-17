from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.models.observation import Observation
from app.models.semantic import SemanticConcept
from app.semantic_engine.engine import recompute_semantics
from app.semantic_engine.resolver import extract_concepts


def test_semantic_resolver_extracts_durable_concepts_from_article_title():
    concepts = extract_concepts(
        "Nvidia dramatically reduces amount of OpenAI infra financing it may guarantee",
        {"title": "Nvidia dramatically reduces amount of OpenAI infra financing it may guarantee"},
        "hacker_news",
        "story_score",
    )
    keys = {item.canonical_key for item in concepts}
    assert "nvidia" in keys
    assert "openai" in keys
    assert "ai infrastructure" in keys
    article = next(item for item in concepts if item.method == "title_fallback_v1")
    assert article.confidence < 0.8


def test_semantic_history_is_append_only_and_deduplicated_per_version():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add_all([
            Observation(
                source="reddit", source_ref="1", topic="social running", metric="mentions", value=1.0,
                observed_at=now - timedelta(hours=1), payload={"title": "Social running clubs grow"},
                content_hash="a" * 64,
            ),
            Observation(
                source="news", source_ref="2", topic="AI agents", metric="coverage", value=2.0,
                observed_at=now, payload={"title": "Agentic AI tools expand"},
                content_hash="b" * 64,
            ),
        ])
        db.commit()
        first = recompute_semantics(db, hours=24)
        assert first["status"] == "succeeded"
        first_count = len(list(db.scalars(select(SemanticConcept))))
        assert first_count > 0
        second = recompute_semantics(db, hours=24)
        assert second["status"] == "succeeded"
        second_count = len(list(db.scalars(select(SemanticConcept))))
        assert second_count == first_count
        keys = {row.canonical_key for row in db.scalars(select(SemanticConcept))}
        assert "running clubs" in keys
        assert "ai agents" in keys


def test_semantic_curator_agent_is_registered():
    from app.agent_orchestration.registry import registry
    manifest = registry.get("semantic_curator").manifest()
    assert manifest.role == "Semantic Curator"
    assert "read:semantic_concepts" in manifest.permissions
