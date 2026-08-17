from collections import defaultdict

from app.feature_engine.contracts import ExtractedFeature, FeatureExtractorManifest
from app.feature_engine.utils import hashed_embedding, normalize_topic
from app.models.observation import Observation


class SemanticFeatureExtractor:
    def manifest(self) -> FeatureExtractorManifest:
        return FeatureExtractorManifest(
            "semantic_fingerprint", "1.0",
            "Creates deterministic semantic fingerprints; replaceable by embedding providers later.",
            ("semantic",),
        )

    def extract(self, observations: list[Observation]) -> list[ExtractedFeature]:
        grouped: dict[str, list[Observation]] = defaultdict(list)
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                grouped[topic].append(item)
        output: list[ExtractedFeature] = []
        for topic, items in grouped.items():
            text = " ".join([topic] + [str(item.payload.get("title", "")) for item in items])
            output.append(ExtractedFeature(
                topic, "semantic", "embedding", vector=hashed_embedding(text), window="window",
                confidence=0.7, evidence_ids=[item.id for item in items],
                attributes={"method": "hashed-bag-of-words-v1", "dimensions": 24},
            ))
        return output
