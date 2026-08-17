from datetime import datetime, timezone

from app.signal_engine.contracts import ObservationInput
from app.signal_engine.hashing import observation_hash
from app.signal_engine.registry import registry


def test_registry_exposes_expected_connectors() -> None:
    ids = {connector.manifest().id for connector in registry.all()}
    assert {"demo", "hacker_news", "reddit", "google_trends"}.issubset(ids)


def test_observation_hash_is_deterministic() -> None:
    observation = ObservationInput(
        source="test",
        source_ref="1",
        topic="running clubs",
        metric="mentions",
        value=12.0,
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        payload={"b": 2, "a": 1},
    )
    assert observation_hash(observation) == observation_hash(observation)
    assert len(observation_hash(observation)) == 64
