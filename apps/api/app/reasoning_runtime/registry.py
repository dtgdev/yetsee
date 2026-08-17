from __future__ import annotations

from app.reasoning_runtime.contracts import Reasoner


class ReasonerRegistry:
    def __init__(self) -> None:
        self._reasoners: dict[str, Reasoner] = {}

    def register(self, reasoner: Reasoner) -> None:
        manifest = reasoner.manifest()
        if manifest.id in self._reasoners:
            raise ValueError(f"Reasoner already registered: {manifest.id}")
        self._reasoners[manifest.id] = reasoner

    def get(self, reasoner_id: str) -> Reasoner:
        try:
            return self._reasoners[reasoner_id]
        except KeyError as exc:
            raise KeyError(f"Unknown reasoner: {reasoner_id}") from exc

    def all(self) -> list[Reasoner]:
        return [self._reasoners[key] for key in sorted(self._reasoners)]


registry = ReasonerRegistry()
