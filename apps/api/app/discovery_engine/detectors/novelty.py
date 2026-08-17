from app.discovery_engine.contracts import Detection, DetectorManifest
from app.discovery_engine.utils import clamp, normalize_topic, recency_weight
from app.models.feature import Feature
from app.models.observation import Observation


class NoveltyDetector:
    def manifest(self) -> DetectorManifest:
        return DetectorManifest("novelty", "1.0", "Surfaces recent topics with little accumulated evidence history.")

    def detect(self, observations: list[Observation], features: list[Feature] | None = None) -> list[Detection]:
        grouped: dict[str, list[Observation]] = {}
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                grouped.setdefault(topic, []).append(item)
        output: list[Detection] = []
        for topic, items in grouped.items():
            newest = max(items, key=lambda x: x.observed_at)
            from app.discovery_engine.utils import age_hours
            freshness = recency_weight(age_hours(newest), half_life=168)
            rarity = 1.0 / max(1, len(items))
            strength = clamp(0.55 * freshness + 0.45 * rarity)
            if strength < 0.35:
                continue
            output.append(Detection(
                subject=topic,
                kind="novelty",
                strength=strength,
                confidence=clamp(0.45 + freshness * 0.35),
                evidence_ids=[item.id for item in items[-8:]],
                explanation=f"{topic} is relatively new in the current Signal Lake window.",
                attributes={"observation_count": len(items), "freshness": freshness},
            ))
        return output
