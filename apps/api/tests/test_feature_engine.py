from datetime import datetime, timedelta, timezone

from app.feature_engine.extractors.semantic import SemanticFeatureExtractor
from app.feature_engine.extractors.source import SourceFeatureExtractor
from app.feature_engine.extractors.statistical import StatisticalFeatureExtractor
from app.feature_engine.extractors.temporal import TemporalFeatureExtractor
from app.models.observation import Observation


def observation(topic: str, source: str, value: float, hours_ago: int, suffix: str) -> Observation:
    return Observation(
        id=f"obs-{suffix}",
        source=source,
        topic=topic,
        metric="interest",
        value=value,
        observed_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        payload={"title": topic},
        content_hash=(suffix * 64)[:64],
    )


def test_feature_extractors_are_deterministic_and_evidence_linked():
    observations = [
        observation("running clubs", "google_trends", 0.2, 72, "a"),
        observation("running clubs", "reddit", 0.5, 24, "b"),
        observation("running clubs", "youtube", 0.8, 1, "c"),
    ]
    temporal = TemporalFeatureExtractor().extract(observations)
    statistical = StatisticalFeatureExtractor().extract(observations)
    source = SourceFeatureExtractor().extract(observations)
    semantic = SemanticFeatureExtractor().extract(observations)
    assert {item.name for item in temporal} >= {"velocity", "acceleration", "observation_count"}
    assert {item.name for item in statistical} >= {"frequency", "volatility", "rarity"}
    assert source[0].attributes["source_count"] == 3
    assert len(semantic[0].vector) == 24
    assert semantic[0].vector == SemanticFeatureExtractor().extract(observations)[0].vector
    assert set(temporal[0].evidence_ids) == {"obs-a", "obs-b", "obs-c"}
