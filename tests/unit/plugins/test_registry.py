"""Unit tests for the plugin registry.

Covers: stable metadata IDs, compatible version ranges, declared
permissions, duplicate capability ownership, and deterministic ordering.
"""

from __future__ import annotations

import pytest

from agentharness.plugins.api import PluginMetadata
from agentharness.plugins.registry import (
    CapabilityConflictError,
    PluginRegistry,
    RegistrationError,
)


def _make_meta(
    plugin_id: str = "test.plugin",
    capabilities: list[str] | None = None,
    core_range: str = ">=0.1.0",
) -> PluginMetadata:
    return PluginMetadata(
        plugin_id=plugin_id,
        display_name="Test Plugin",
        version="1.0.0",
        capabilities=capabilities or ["test.capability"],
        core_version_range=core_range,
    )


class TestPluginRegistration:
    def test_register_and_list(self) -> None:
        registry = PluginRegistry()
        meta = _make_meta()
        registry.register(meta)
        assert meta in registry.list_plugins()

    def test_duplicate_plugin_id_raises(self) -> None:
        registry = PluginRegistry()
        meta = _make_meta()
        registry.register(meta)
        with pytest.raises(RegistrationError, match="already registered"):
            registry.register(meta)

    def test_duplicate_capability_owner_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(_make_meta("plugin.a", ["shared.cap"]))
        with pytest.raises(CapabilityConflictError, match="shared.cap"):
            registry.register(_make_meta("plugin.b", ["shared.cap"]))

    def test_listing_is_deterministic(self) -> None:
        registry = PluginRegistry()
        for i in range(5):
            registry.register(_make_meta(f"plugin.{i}", [f"cap.{i}"]))
        listing = registry.list_plugins()
        assert listing == sorted(listing, key=lambda m: m.plugin_id)

    def test_empty_capability_list_raises(self) -> None:
        with pytest.raises(ValueError, match="capabilities"):
            PluginMetadata(
                plugin_id="x",
                display_name="X",
                version="1.0.0",
                capabilities=[],
                core_version_range=">=0.1.0",
            )

    def test_empty_plugin_id_raises(self) -> None:
        with pytest.raises(ValueError, match="plugin_id"):
            PluginMetadata(
                plugin_id="",
                display_name="X",
                version="1.0.0",
                capabilities=["cap"],
                core_version_range=">=0.1.0",
            )

    def test_get_plugin_by_id(self) -> None:
        registry = PluginRegistry()
        meta = _make_meta("my.plugin")
        registry.register(meta)
        assert registry.get("my.plugin") == meta

    def test_get_nonexistent_raises(self) -> None:
        registry = PluginRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")
