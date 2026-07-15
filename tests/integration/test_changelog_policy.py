"""Integration tests for changelog policy."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.core.changelog import (
    ChangelogStrategy,
    detect_changelog_policy,
)


class TestChangelogPolicyIntegration:
    def test_towncrier_fragment_dir(self, tmp_path: Path) -> None:
        (tmp_path / "changelog.d").mkdir()
        result = detect_changelog_policy(tmp_path)
        assert result.strategy == ChangelogStrategy.TOWNCRIER

    def test_keepachangelog_format(self, tmp_path: Path) -> None:
        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\nFormat follows [Keep a Changelog](https://keepachangelog.com/).\n"
        )
        result = detect_changelog_policy(tmp_path)
        assert result.strategy == ChangelogStrategy.KEEPACHANGELOG

    def test_no_changelog_is_absent(self, tmp_path: Path) -> None:
        assert detect_changelog_policy(tmp_path).strategy == ChangelogStrategy.ABSENT
