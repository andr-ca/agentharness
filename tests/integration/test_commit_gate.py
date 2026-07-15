"""Integration tests for the commit gate context reader."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentharness.gates.commit import read_commit_context


class TestCommitGate:
    def test_empty_repo_has_no_staged_files(self, tmp_path: Path) -> None:
        ctx = read_commit_context(tmp_path)
        assert ctx.staged_files == []

    def test_context_carries_repo_root(self, tmp_path: Path) -> None:
        ctx = read_commit_context(tmp_path)
        assert ctx.repo_root == tmp_path
