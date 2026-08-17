from datetime import datetime, timedelta, timezone

from app.discovery_engine.detectors.acceleration import AccelerationDetector
from app.discovery_engine.detectors.novelty import NoveltyDetector
from app.discovery_engine.detectors.graph_community import GraphCommunityDetector
from app.discovery_engine.detectors.semantic import SemanticClusterDetector
from app.discovery_engine.detectors.velocity import VelocityDetector
from app.models.observation import Observation


def obs(topic: str, hours_ago: int, value: float, suffix: str) -> Observation:
    return Observation(
        id=f"00000000-0000-0000-0000-{suffix:0>12}",
        source="test",
        source_ref=suffix,
        topic=topic,
        metric="mentions",
        value=value,
        observed_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        payload={},
        content_hash=(suffix * 64)[:64],
    )


def sample():
    return [
        obs("running clubs", 120, 0.10, "1"),
        obs("social running", 72, 0.18, "2"),
        obs("running clubs", 24, 0.42, "3"),
        obs("running clubs", 6, 0.66, "4"),
        obs("social running clubs", 2, 0.71, "5"),
    ]


def test_detector_manifests_are_stable():
    ids = {d.manifest().id for d in [VelocityDetector(), AccelerationDetector(), NoveltyDetector(), SemanticClusterDetector(), GraphCommunityDetector()]}
    assert ids == {"velocity", "acceleration", "novelty", "semantic_cluster", "graph_community"}


def test_detectors_surface_candidates():
    observations = sample()
    detections = []
    for detector in [VelocityDetector(), AccelerationDetector(), NoveltyDetector(), SemanticClusterDetector(), GraphCommunityDetector()]:
        detections.extend(detector.detect(observations))
    assert detections
    assert all(0 <= item.strength <= 1 for item in detections)
    assert all(item.evidence_ids for item in detections)
    assert any(item.kind == "semantic_cluster" for item in detections)
