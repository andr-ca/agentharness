"""Unit tests for legacy profile migration.

Legacy `.agentharness-profile` files contain a plain tier name (prototype,
internal, production).  Migration imports the tier and coverage data with
provenance metadata, rejecting ambiguous or weakening changes.
"""

from __future__ import annotations

import pytest

from agentharness.profile.migrate import (
    LegacyProfile,
    MigrationConflictError,
    import_legacy_profile,
)


class TestLegacyProfileParse:
    def test_parse_production_tier(self) -> None:
        profile = LegacyProfile.parse("production")
        assert profile.tier == "production"

    def test_parse_internal_tier(self) -> None:
        profile = LegacyProfile.parse("internal")
        assert profile.tier == "internal"

    def test_parse_prototype_tier(self) -> None:
        profile = LegacyProfile.parse("prototype")
        assert profile.tier == "prototype"

    def test_unknown_tier_enters_legacy_deferred(self) -> None:
        profile = LegacyProfile.parse("my-custom-tier")
        assert profile.tier == "legacy-deferred"
        assert profile.raw_selector == "my-custom-tier"

    def test_empty_selector_raises(self) -> None:
        with pytest.raises(MigrationConflictError, match="selector"):
            LegacyProfile.parse("")


class TestImportLegacyProfile:
    def test_import_production_returns_mapped_record(self) -> None:
        record = import_legacy_profile("production")
        assert record["tier"] == "production"
        assert "provenance" in record
        assert record["provenance"]["source"] == "legacy-.agentharness-profile"

    def test_import_internal_returns_mapped_record(self) -> None:
        record = import_legacy_profile("internal")
        assert record["tier"] == "internal"

    def test_import_deferred_sets_legacy_deferred_tier(self) -> None:
        record = import_legacy_profile("custom-ecosystem")
        assert record["tier"] == "legacy-deferred"
        assert record["provenance"]["legacy_selector"] == "custom-ecosystem"

    def test_import_empty_raises(self) -> None:
        with pytest.raises(MigrationConflictError):
            import_legacy_profile("")
