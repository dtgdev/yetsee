from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.agent_orchestration.registry import registry as agent_registry
from app.discovery_engine.registry import registry as detector_registry
from app.feature_engine.registry import registry as feature_registry
from app.signal_engine.registry import registry as connector_registry


class KernelPluginRegistry:
    """Read-only registry that exposes existing extension systems through one kernel view."""

    def all(self) -> list[dict[str, Any]]:
        plugins: list[dict[str, Any]] = []
        for plugin_type, registry in (
            ("connector", connector_registry),
            ("feature_extractor", feature_registry),
            ("discovery_model", detector_registry),
            ("agent", agent_registry),
        ):
            for implementation in registry.all():
                raw = implementation.manifest().__dict__
                plugins.append(
                    {
                        "id": raw.get("id") or raw.get("name"),
                        "type": plugin_type,
                        "version": raw.get("version", "1.0.0"),
                        "description": raw.get("description", ""),
                        "capabilities": raw.get("capabilities", []),
                        "permissions": raw.get("permissions", []),
                        "metadata": raw,
                    }
                )
        return sorted(plugins, key=lambda p: (p["type"], str(p["id"])))

    def summary(self) -> dict[str, Any]:
        plugins = self.all()
        counts: dict[str, int] = {}
        for plugin in plugins:
            counts[plugin["type"]] = counts.get(plugin["type"], 0) + 1
        return {"plugins": len(plugins), "types": counts}


registry = KernelPluginRegistry()
