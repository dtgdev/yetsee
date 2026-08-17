from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ReasonerManifest:
    id: str
    name: str
    version: str
    scientific_question: str
    evidence_types: tuple[str, ...] = ()
    deterministic: bool = True


@dataclass(frozen=True)
class ReasoningOutput:
    conclusion: str
    confidence: float
    support_level: str
    supporting_factors: list[dict[str, Any]] = field(default_factory=list)
    contradicting_factors: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    recommended_evidence: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""


class Reasoner(Protocol):
    def manifest(self) -> ReasonerManifest: ...
    def execute(self, db: Session, investigation_id: str) -> ReasoningOutput: ...
