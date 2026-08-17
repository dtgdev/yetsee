from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConceptCandidate:
    canonical_name: str
    canonical_key: str
    kind: str
    mention_text: str
    confidence: float
    method: str
    attributes: dict[str, Any] = field(default_factory=dict)
