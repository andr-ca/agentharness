"""Integration tests for plugin CLI commands.

Covers: plugins list, plugins inspect, and trust workflow producing a
plan rather than a direct registry mutation.
"""

from __future__ import annotations

from agentharness.plugins.api import PluginMetadata
from agentharness.plugins.registry import PluginRegistry
from agentharness.plugins.trust import TrustEntry, TrustRegistry


class TestPluginListCommand:
    def test_empty_registry_returns_empty_list(self) -> None:
        registry = PluginRegistry()
        assert registry.list_plugins() == []

    def test_registered_plugin_appears_in_list(self) -> None:
        registry = PluginRegistry()
        meta = PluginMetadata(
            plugin_id="test.plugin",
            display_name="Test",
            version="1.0.0",
            capabilities=["test.cap"],
            core_version_range=">=0.1.0",
        )
        registry.register(meta)
        listing = registry.list_plugins()
        assert len(listing) == 1
        assert listing[0].plugin_id == "test.plugin"


class TestPluginInspectCommand:
    def test_inspect_returns_full_metadata(self) -> None:
        registry = PluginRegistry()
        meta = PluginMetadata(
            plugin_id="inspect.target",
            display_name="Inspectable",
            version="2.3.4",
            capabilities=["cap.a", "cap.b"],
            core_version_range=">=0.1.0",
        )
        registry.register(meta)
        retrieved = registry.get("inspect.target")
        assert retrieved.version == "2.3.4"
        assert "cap.a" in retrieved.capabilities


class TestPluginTrustWorkflow:
    def test_propose_add_does_not_mutate_registry(self) -> None:
        trust = TrustRegistry()
        entry = TrustEntry(plugin_id="new.plugin", pinned_version="1.0.0")
        plan = trust.propose_add(entry)
        assert "new.plugin" in plan
        # Registry is unchanged until add() is called with committed data
        assert not trust.is_trusted("new.plugin", "1.0.0")

    def test_add_after_commit_enables_trust(self) -> None:
        trust = TrustRegistry()
        entry = TrustEntry(plugin_id="trusted.plugin", pinned_version="3.1.0")
        trust.add(entry)
        assert trust.is_trusted("trusted.plugin", "3.1.0")
        assert not trust.is_trusted("trusted.plugin", "3.2.0")
