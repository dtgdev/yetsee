from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class ConnectorManifest:
    id: str
    version: str
    description: str
    schedule: str
    supports_history: bool = False
    supports_incremental: bool = True
    requires_api_key: bool = False


@dataclass(frozen=True)
class RawItem:
    source_ref: str
    observed_at: datetime
    payload: dict[str, Any]


@dataclass(frozen=True)
class ObservationInput:
    source: str
    source_ref: str | None
    topic: str | None
    metric: str
    value: float | None
    observed_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FetchPage:
    items: list[RawItem]
    next_cursor: str | None = None


class Connector(Protocol):
    def manifest(self) -> ConnectorManifest: ...

    def fetch(self, cursor: str | None = None) -> FetchPage: ...

    def normalize(self, raw: RawItem) -> ObservationInput: ...

    def validate(self, observation: ObservationInput) -> list[str]: ...
