"""Tests verifying that declared capabilities are owned by registered plugins.

A capability without an owner means the registry has a gap — no plugin
covers it.
"""

from __future__ import annotations

from agentharness.plugins.api import PluginMetadata
from agentharness.plugins.registry import PluginRegistry


EXPECTED_BUNDLED_CAPABILITIES: set[str] = set()
# NOTE: Populated as plugins are added in later tasks.  This set serves as
# the capability census; if a task adds capabilities, add them here too.


class TestCapabilityCoverage:
    def test_all_expected_capabilities_have_an_owner(self) -> None:
        """Every capability in EXPECTED_BUNDLED_CAPABILITIES must be owned."""
        registry = PluginRegistry()
        owned: set[str] = set()
        for meta in registry.list_plugins():
            owned.update(meta.capabilities)
        uncovered = EXPECTED_BUNDLED_CAPABILITIES - owned
        assert not uncovered, f"Uncovered capabilities: {sorted(uncovered)}"

    def test_registry_has_no_phantom_capabilities(self) -> None:
        """No capability can be registered without a matching metadata entry."""
        registry = PluginRegistry()
        # Attempt to add a second registration with a conflicting capability —
        # the registry must detect the conflict.
        from agentharness.plugins.registry import CapabilityConflictError

        meta_a = PluginMetadata(
            plugin_id="owner.a",
            display_name="Owner A",
            version="1.0.0",
            capabilities=["shared.cap"],
            core_version_range=">=0.1.0",
        )
        meta_b = PluginMetadata(
            plugin_id="owner.b",
            display_name="Owner B",
            version="1.0.0",
            capabilities=["shared.cap"],
            core_version_range=">=0.1.0",
        )
        registry.register(meta_a)
        import pytest

        with pytest.raises(CapabilityConflictError):
            registry.register(meta_b)
