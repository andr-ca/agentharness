"""Unit tests for plugin trust management.

Covers: trusted plugin entry requirements, untrusted plugin rejection,
version pinning validation, and that trust changes produce profile plans
rather than mutable registry edits.
"""

from __future__ import annotations

import pytest

from agentharness.plugins.trust import (
    TrustEntry,
    TrustError,
    TrustRegistry,
)


class TestTrustEntry:
    def test_trust_entry_requires_plugin_id_and_version(self) -> None:
        entry = TrustEntry(plugin_id="my.plugin", pinned_version="1.2.3")
        assert entry.plugin_id == "my.plugin"
        assert entry.pinned_version == "1.2.3"

    def test_trust_entry_requires_pinned_version(self) -> None:
        with pytest.raises(TrustError, match="version"):
            TrustEntry(plugin_id="my.plugin", pinned_version="")

    def test_trust_entry_rejects_wildcard_version(self) -> None:
        with pytest.raises(TrustError, match="exact"):
            TrustEntry(plugin_id="my.plugin", pinned_version="*")

    def test_trust_entry_rejects_range_version(self) -> None:
        with pytest.raises(TrustError, match="exact"):
            TrustEntry(plugin_id="my.plugin", pinned_version=">=1.0.0")


class TestTrustRegistry:
    def test_trusted_plugin_can_run(self) -> None:
        registry = TrustRegistry()
        registry.add(TrustEntry(plugin_id="my.plugin", pinned_version="1.0.0"))
        assert registry.is_trusted("my.plugin", "1.0.0")

    def test_untrusted_plugin_cannot_run(self) -> None:
        registry = TrustRegistry()
        assert not registry.is_trusted("unknown.plugin", "1.0.0")

    def test_wrong_version_not_trusted(self) -> None:
        registry = TrustRegistry()
        registry.add(TrustEntry(plugin_id="my.plugin", pinned_version="1.0.0"))
        assert not registry.is_trusted("my.plugin", "2.0.0")

    def test_add_returns_plan_not_direct_mutation(self) -> None:
        """Adding trust must return a plan that the operator applies via commit."""
        registry = TrustRegistry()
        plan = registry.propose_add(
            TrustEntry(plugin_id="new.plugin", pinned_version="1.0.0")
        )
        assert plan is not None
        assert "new.plugin" in str(plan)
        # Registry itself is NOT yet updated
        assert not registry.is_trusted("new.plugin", "1.0.0")

    def test_duplicate_trust_entry_is_idempotent(self) -> None:
        registry = TrustRegistry()
        entry = TrustEntry(plugin_id="my.plugin", pinned_version="1.0.0")
        registry.add(entry)
        registry.add(entry)  # Should not raise
        assert registry.is_trusted("my.plugin", "1.0.0")
