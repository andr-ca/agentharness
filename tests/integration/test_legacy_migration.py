"""Integration tests for legacy profile migration.

Covers: .agentharness-profile file reading, tier import, provenance
recording, and validation of the two-file legacy-deferred state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentharness.profile.migrate import (
    MigrationConflictError,
    import_legacy_profile,
    read_legacy_profile_file,
)


class TestReadLegacyProfileFile:
    def test_reads_tier_from_file(self, tmp_path: Path) -> None:
        profile_file = tmp_path / ".agentharness-profile"
        profile_file.write_text("production\n")
        tier = read_legacy_profile_file(profile_file)
        assert tier == "production"

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        profile_file = tmp_path / ".agentharness-profile"
        profile_file.write_text("  internal  \n")
        tier = read_legacy_profile_file(profile_file)
        assert tier == "internal"

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_legacy_profile_file(tmp_path / ".agentharness-profile")

    def test_empty_file_raises_conflict(self, tmp_path: Path) -> None:
        profile_file = tmp_path / ".agentharness-profile"
        profile_file.write_text("   \n")
        with pytest.raises(MigrationConflictError, match="empty"):
            read_legacy_profile_file(profile_file)


class TestLegacyMigrationProvenanceChain:
    def test_provenance_records_source_file(self) -> None:
        record = import_legacy_profile("production")
        assert record["provenance"]["source"] == "legacy-.agentharness-profile"

    def test_provenance_records_original_selector(self) -> None:
        record = import_legacy_profile("custom")
        assert record["provenance"]["legacy_selector"] == "custom"

    def test_known_tiers_do_not_carry_legacy_deferred(self) -> None:
        for tier in ("production", "internal", "prototype"):
            record = import_legacy_profile(tier)
            assert record["tier"] == tier
            # provenance is present but legacy_selector is set only for deferred
            assert "legacy_selector" not in record["provenance"] or \
                record["provenance"]["legacy_selector"] == tier
