from types import SimpleNamespace

from app.kernel.plugins import registry
from app.kernel.contracts import PluginManifest


def test_kernel_registry_exposes_extension_types():
    plugins = registry.all()
    types = {p["type"] for p in plugins}
    assert "connector" in types
    assert "feature_extractor" in types
    assert "discovery_model" in types
    assert "agent" in types


def test_plugin_manifest_contract_is_stable():
    manifest = PluginManifest(
        id="example",
        type="reasoner",
        version="1.0.0",
        description="Example",
        capabilities=("reason",),
        permissions=("read:investigations",),
    )
    assert manifest.compatible_api == "yetsee.ai/v1alpha1"
    assert manifest.capabilities == ("reason",)
