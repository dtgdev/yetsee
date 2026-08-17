from dataclasses import dataclass, field
from typing import Any, Protocol

from app.models.observation import Observation


@dataclass(frozen=True)
class FeatureExtractorManifest:
    id: str
    version: str
    description: str
    feature_types: tuple[str, ...]


@dataclass
class ExtractedFeature:
    subject: str
    feature_type: str
    name: str
    value: float | None = None
    vector: list[float] = field(default_factory=list)
    window: str | None = None
    confidence: float = 1.0
    evidence_ids: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


class FeatureExtractor(Protocol):
    def manifest(self) -> FeatureExtractorManifest: ...
    def extract(self, observations: list[Observation]) -> list[ExtractedFeature]: ...
