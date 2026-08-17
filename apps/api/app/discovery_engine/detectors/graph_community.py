from collections import defaultdict

from app.discovery_engine.contracts import Detection, DetectorManifest
from app.discovery_engine.utils import clamp
from app.models.feature import Feature
from app.models.observation import Observation


class GraphCommunityDetector:
    def manifest(self) -> DetectorManifest:
        return DetectorManifest(
            "graph_community",
            "1.0",
            "Surfaces graph subjects that are unusually connected inside evidence-backed communities.",
        )

    def detect(self, observations: list[Observation], features: list[Feature] | None = None) -> list[Detection]:
        if not features:
            return []
        by_subject: dict[str, dict[str, Feature]] = defaultdict(dict)
        for feature in features:
            if feature.feature_type == "graph":
                by_subject[feature.subject][feature.name] = feature
        output: list[Detection] = []
        for subject, rows in by_subject.items():
            sample = next(iter(rows.values()))
            if sample.attributes.get("entity_kind") in {"source", "metric"}:
                continue
            centrality = rows.get("degree_centrality")
            degree = rows.get("degree")
            community = rows.get("community")
            if centrality is None or centrality.value is None or centrality.value < 0.35:
                continue
            evidence_ids = list(dict.fromkeys(
                eid for row in rows.values() for eid in row.evidence_ids
            ))
            output.append(
                Detection(
                    subject=subject,
                    kind="graph_community",
                    strength=clamp(centrality.value),
                    confidence=clamp(0.55 + min(len(evidence_ids), 10) * 0.035),
                    evidence_ids=evidence_ids,
                    explanation=(
                        f"{subject} is a relatively connected graph node with degree "
                        f"{int(degree.value if degree and degree.value is not None else 0)} "
                        f"in community {int(community.value if community and community.value is not None else 0)}."
                    ),
                    attributes={
                        "degree": degree.value if degree else 0,
                        "degree_centrality": centrality.value,
                        "community": community.value if community else None,
                        "feature_backed": True,
                    },
                )
            )
        return output
