from collections import defaultdict

from app.feature_engine.contracts import ExtractedFeature, FeatureExtractorManifest
from app.feature_engine.utils import clamp, normalize_topic
from app.models.observation import Observation


class TemporalFeatureExtractor:
    def manifest(self) -> FeatureExtractorManifest:
        return FeatureExtractorManifest(
            "temporal", "1.0", "Computes reusable velocity, acceleration and trend features by topic.",
            ("temporal",),
        )

    def extract(self, observations: list[Observation]) -> list[ExtractedFeature]:
        grouped: dict[str, list[Observation]] = defaultdict(list)
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                grouped[topic].append(item)
        output: list[ExtractedFeature] = []
        for topic, items in grouped.items():
            items.sort(key=lambda item: item.observed_at)
            evidence_ids = [item.id for item in items]
            midpoint = max(1, len(items) // 2)
            old_count, new_count = midpoint, len(items) - midpoint
            velocity = clamp((new_count + 1) / max(1, old_count + 1) / 2.0)
            values = [item.value for item in items if item.value is not None]
            delta = (values[-1] - values[0]) if len(values) >= 2 else 0.0
            acceleration = clamp(0.5 + delta / 2.0)
            output.extend([
                ExtractedFeature(topic, "temporal", "velocity", velocity, window="window", confidence=min(1.0, 0.4 + len(items) / 20), evidence_ids=evidence_ids, attributes={"earlier_count": old_count, "recent_count": new_count}),
                ExtractedFeature(topic, "temporal", "acceleration", acceleration, window="window", confidence=min(1.0, 0.4 + len(items) / 20), evidence_ids=evidence_ids, attributes={"value_delta": delta}),
                ExtractedFeature(topic, "temporal", "observation_count", float(len(items)), window="window", confidence=1.0, evidence_ids=evidence_ids),
            ])
        return output
