from app.discovery_engine.detectors.acceleration import AccelerationDetector
from app.discovery_engine.detectors.graph_community import GraphCommunityDetector
from app.discovery_engine.detectors.novelty import NoveltyDetector
from app.discovery_engine.detectors.semantic import SemanticClusterDetector
from app.discovery_engine.detectors.velocity import VelocityDetector


class DetectorRegistry:
    def __init__(self):
        self._detectors = {
            detector.manifest().id: detector
            for detector in [
                VelocityDetector(),
                AccelerationDetector(),
                NoveltyDetector(),
                SemanticClusterDetector(),
                GraphCommunityDetector(),
            ]
        }

    def all(self):
        return list(self._detectors.values())

    def get(self, detector_id: str):
        return self._detectors[detector_id]


registry = DetectorRegistry()
