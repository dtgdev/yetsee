from collections import defaultdict

from app.discovery_engine.contracts import Detection, DetectorManifest
from app.discovery_engine.utils import clamp, normalize_topic
from app.models.feature import Feature
from app.models.observation import Observation


class AccelerationDetector:
    def manifest(self) -> DetectorManifest:
        return DetectorManifest("acceleration", "1.1", "Detects increasing intensity using shared temporal features when available.")

    def detect(self, observations: list[Observation], features: list[Feature] | None = None) -> list[Detection]:
        if features:
            output = []
            for feature in features:
                if feature.feature_type == "temporal" and feature.name == "acceleration" and feature.value is not None and feature.value >= 0.3:
                    output.append(Detection(
                        subject=feature.subject,
                        kind="acceleration",
                        strength=clamp(feature.value),
                        confidence=feature.confidence,
                        evidence_ids=feature.evidence_ids,
                        explanation=f"Shared temporal features show increasing signal intensity for {feature.subject}.",
                        attributes={"feature_id": feature.id, "feature_backed": True},
                    ))
            if output:
                return output
        grouped: dict[str, list[Observation]] = defaultdict(list)
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                grouped[topic].append(item)
        output = []
        for topic, items in grouped.items():
            items = sorted(items, key=lambda x: x.observed_at)
            if len(items) < 3:
                continue
            values = [item.value for item in items if item.value is not None]
            value_growth = max(0.0, values[-1] - values[0]) if len(values) >= 2 else 0.0
            strength = clamp(0.35 + value_growth)
            if strength >= 0.3:
                output.append(Detection(topic, "acceleration", strength, clamp(0.5 + len(items) / 30), [item.id for item in items[-12:]], f"{topic} shows increasing signal intensity across the observed window.", {"value_growth": value_growth, "feature_backed": False}))
        return output
