from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AgentManifest:
    id: str
    version: str
    role: str
    description: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]


@dataclass
class AgentTaskContext:
    task_id: str
    task_type: str
    target_type: str | None
    target_id: str | None
    inputs: dict[str, Any]
    constraints: dict[str, Any]


@dataclass
class FindingDraft:
    category: str
    title: str
    detail: str
    severity: str = "info"
    stance: str = "neutral"
    confidence: float = 0.5
    evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    status: str = "completed"
    summary: str = ""
    recommendation: str | None = None
    confidence: float = 0.5
    findings: list[FindingDraft] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)
    permissions_used: list[str] = field(default_factory=list)


class YetSeeAgent(Protocol):
    def manifest(self) -> AgentManifest: ...
    def execute(self, db: Session, context: AgentTaskContext) -> AgentResult: ...
