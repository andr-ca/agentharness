"""Integration tests for legacy-deferred coexistence state.

The only valid two-file state is a declared legacy-deferred requirement.
Undeclared coexistence, changed inputs, conflicting precedence, or
unstructured exceptions must be rejected.
"""

from __future__ import annotations

import pytest

from agentharness.profile.migrate import (
    LegacyProfile,
    MigrationConflictError,
    import_legacy_profile,
)


class TestLegacyDeferredCoexistence:
    def test_unknown_tier_produces_legacy_deferred(self) -> None:
        record = import_legacy_profile("custom-ecosystem")
        assert record["tier"] == "legacy-deferred"

    def test_legacy_deferred_carries_original_selector(self) -> None:
        record = import_legacy_profile("my-ecosystem")
        assert record["provenance"]["legacy_selector"] == "my-ecosystem"

    def test_known_tier_does_not_produce_legacy_deferred(self) -> None:
        for tier in ("production", "internal", "prototype"):
            record = import_legacy_profile(tier)
            assert record["tier"] != "legacy-deferred"

    def test_empty_selector_always_raises(self) -> None:
        with pytest.raises(MigrationConflictError, match="selector"):
            import_legacy_profile("")

    def test_whitespace_only_selector_raises(self) -> None:
        with pytest.raises(MigrationConflictError, match="selector"):
            import_legacy_profile("   ")
