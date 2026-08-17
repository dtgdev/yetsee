from collections import defaultdict

from app.discovery_engine.contracts import Detection, DetectorManifest
from app.discovery_engine.utils import clamp, normalize_topic, tokens
from app.models.feature import Feature
from app.models.observation import Observation


class SemanticClusterDetector:
    def manifest(self) -> DetectorManifest:
        return DetectorManifest("semantic_cluster", "1.0", "Groups lexically/semantically similar topic labels without external model dependencies.")

    def detect(self, observations: list[Observation], features: list[Feature] | None = None) -> list[Detection]:
        topics: dict[str, list[Observation]] = defaultdict(list)
        for item in observations:
            topic = normalize_topic(item.topic)
            if topic:
                topics[topic].append(item)
        names = list(topics)
        visited: set[str] = set()
        output: list[Detection] = []
        for name in names:
            if name in visited:
                continue
            base = tokens(name)
            cluster = [name]
            for other in names:
                if other == name or other in visited:
                    continue
                second = tokens(other)
                if not base or not second:
                    continue
                similarity = len(base & second) / len(base | second)
                if similarity >= 0.34:
                    cluster.append(other)
            for item in cluster:
                visited.add(item)
            evidence = [obs for topic in cluster for obs in topics[topic]]
            if len(cluster) < 2 and len(evidence) < 3:
                continue
            subject = max(cluster, key=lambda x: len(topics[x]))
            strength = clamp(0.42 + 0.12 * (len(cluster) - 1) + min(len(evidence), 10) * 0.035)
            output.append(Detection(
                subject=subject,
                kind="semantic_cluster",
                strength=strength,
                confidence=clamp(0.55 + min(len(evidence), 12) / 30),
                evidence_ids=[item.id for item in evidence[-15:]],
                explanation=f"Related evidence forms a cluster around {subject}.",
                attributes={"cluster_topics": cluster, "cluster_size": len(evidence), "method": "token-jaccard-baseline"},
            ))
        return output
