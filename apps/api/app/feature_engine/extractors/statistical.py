from collections import defaultdict
import math

from app.feature_engine.contracts import ExtractedFeature, FeatureExtractorManifest
from app.feature_engine.utils import normalize_topic
from app.models.observation import Observation


class StatisticalFeatureExtractor:
    def manifest(self) -> FeatureExtractorManifest:
        return FeatureExtractorManifest("statistics", "1.0", "Computes frequency, mean, volatility and rarity features.", ("statistical",))

    def extract(self, observations: list[Observation]) -> list[ExtractedFeature]:
        grouped: dict[str, list[Observation]] = defaultdict(list)
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                grouped[topic].append(item)
        total = max(1, len(observations))
        output: list[ExtractedFeature] = []
        for topic, items in grouped.items():
            values = [item.value for item in items if item.value is not None]
            mean = sum(values) / len(values) if values else 0.0
            variance = sum((value - mean) ** 2 for value in values) / len(values) if values else 0.0
            evidence_ids = [item.id for item in items]
            output.extend([
                ExtractedFeature(topic, "statistical", "frequency", len(items) / total, window="window", evidence_ids=evidence_ids),
                ExtractedFeature(topic, "statistical", "mean_value", mean, window="window", evidence_ids=evidence_ids),
                ExtractedFeature(topic, "statistical", "volatility", math.sqrt(variance), window="window", evidence_ids=evidence_ids),
                ExtractedFeature(topic, "statistical", "rarity", 1.0 / max(1, len(items)), window="window", evidence_ids=evidence_ids),
            ])
        return output
