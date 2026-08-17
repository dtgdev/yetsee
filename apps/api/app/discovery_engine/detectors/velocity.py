from collections import defaultdict

from app.discovery_engine.contracts import Detection, DetectorManifest
from app.discovery_engine.utils import clamp, normalize_topic
from app.models.feature import Feature
from app.models.observation import Observation


class VelocityDetector:
    def manifest(self) -> DetectorManifest:
        return DetectorManifest("velocity", "1.1", "Detects recent observation-rate increases using shared temporal features when available.")

    def detect(self, observations: list[Observation], features: list[Feature] | None = None) -> list[Detection]:
        if features:
            output = []
            for feature in features:
                if feature.feature_type == "temporal" and feature.name == "velocity" and feature.value is not None and feature.value >= 0.25:
                    output.append(Detection(
                        subject=feature.subject,
                        kind="velocity",
                        strength=clamp(feature.value),
                        confidence=feature.confidence,
                        evidence_ids=feature.evidence_ids,
                        explanation=f"Shared temporal features show elevated evidence velocity for {feature.subject}.",
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
            if len(items) < 2:
                continue
            midpoint = max(1, len(items) // 2)
            old, recent = items[:midpoint], items[midpoint:]
            ratio = (len(recent) + 1) / (len(old) + 1)
            strength = clamp((ratio - 0.5) / 2.0)
            if strength >= 0.25:
                output.append(Detection(topic, "velocity", strength, clamp(0.45 + min(len(items), 12) / 24), [item.id for item in items[-12:]], f"Recent evidence rate for {topic} is {ratio:.2f}x its earlier rate.", {"recent_count": len(recent), "earlier_count": len(old), "ratio": ratio, "feature_backed": False}))
        return output
