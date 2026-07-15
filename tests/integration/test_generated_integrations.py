"""Integration tests for Tasks 5-6: generated conflicts and agent generation."""

from __future__ import annotations

from pathlib import Path

from agentharness.integrations.agents import find_canonical_source, list_generated_clients
from agentharness.integrations.managed_block import apply_managed_block


class TestGeneratedConflicts:
    def test_managed_block_is_idempotent(self) -> None:
        """Applying the same plan twice produces the same result."""
        content = "my block content"
        result1 = apply_managed_block("", "test-id", content)
        result2 = apply_managed_block(result1, "test-id", content)
        assert result1 == result2

    def test_managed_block_does_not_touch_unrelated_content(self) -> None:
        existing = "header content\n"
        result = apply_managed_block(existing, "test", "block")
        assert "header content" in result


class TestAgentGeneration:
    def test_canonical_source_required_for_generation(self, tmp_path: Path) -> None:
        """Without a canonical source (CLAUDE.md), generation cannot proceed."""
        source = find_canonical_source(tmp_path)
        assert source is None

    def test_with_source_generation_is_possible(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Source\n")
        source = find_canonical_source(tmp_path)
        assert source is not None
        assert source.exists()
