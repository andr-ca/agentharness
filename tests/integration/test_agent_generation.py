"""Integration tests for agent source generation correctness."""

from __future__ import annotations

from pathlib import Path

from agentharness.integrations.agents import find_canonical_source, list_generated_clients


class TestAgentSourceGeneration:
    def test_finds_claude_md_as_source(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Source\n")
        source = find_canonical_source(tmp_path)
        assert source is not None and source.name == "CLAUDE.md"

    def test_generated_clients_only_include_existing(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Agents\n")
        clients = list_generated_clients(tmp_path)
        names = {c.name for c in clients}
        assert "AGENTS.md" in names
        # GEMINI.md doesn't exist, so it should not be listed
        assert "GEMINI.md" not in names

    def test_no_generated_clients_returns_empty(self, tmp_path: Path) -> None:
        clients = list_generated_clients(tmp_path)
        assert clients == []
