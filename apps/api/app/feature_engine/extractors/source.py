from collections import defaultdict

from app.feature_engine.contracts import ExtractedFeature, FeatureExtractorManifest
from app.feature_engine.utils import normalize_topic
from app.models.observation import Observation


class SourceFeatureExtractor:
    def manifest(self) -> FeatureExtractorManifest:
        return FeatureExtractorManifest("source", "1.0", "Computes cross-source diversity and agreement features.", ("source",))

    def extract(self, observations: list[Observation]) -> list[ExtractedFeature]:
        grouped: dict[str, list[Observation]] = defaultdict(list)
        all_sources = {item.source for item in observations}
        denominator = max(1, len(all_sources))
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                grouped[topic].append(item)
        output: list[ExtractedFeature] = []
        for topic, items in grouped.items():
            sources = sorted({item.source for item in items})
            output.append(ExtractedFeature(
                topic, "source", "source_diversity", len(sources) / denominator,
                window="window", confidence=1.0, evidence_ids=[item.id for item in items],
                attributes={"sources": sources, "source_count": len(sources)},
            ))
        return output
