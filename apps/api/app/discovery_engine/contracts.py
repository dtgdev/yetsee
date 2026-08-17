from dataclasses import dataclass, field
from typing import Any, Protocol

from app.models.feature import Feature
from app.models.observation import Observation


@dataclass(frozen=True)
class DetectorManifest:
    id: str
    version: str
    description: str


@dataclass
class Detection:
    subject: str
    kind: str
    strength: float
    confidence: float
    evidence_ids: list[str]
    explanation: str
    attributes: dict[str, Any] = field(default_factory=dict)


class DiscoveryDetector(Protocol):
    def manifest(self) -> DetectorManifest: ...
    def detect(self, observations: list[Observation], features: list[Feature] | None = None) -> list[Detection]: ...
