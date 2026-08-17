from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class PluginManifest:
    id: str
    type: str
    version: str
    description: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    compatible_api: str = "yetsee.ai/v1alpha1"


class YetSeePlugin(Protocol):
    def manifest(self) -> PluginManifest: ...
    def validate(self, context: dict[str, Any]) -> None: ...
    def execute(self, context: dict[str, Any]) -> dict[str, Any]: ...
    def explain(self) -> str: ...
    def health(self) -> dict[str, Any]: ...
