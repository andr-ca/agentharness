"""Integration tests for the push gate context reader."""

from __future__ import annotations

from pathlib import Path

from agentharness.gates.push import read_push_context


class TestPushGate:
    def test_empty_stdin_produces_no_updates(self, tmp_path: Path) -> None:
        ctx = read_push_context(tmp_path, stdin_text="")
        assert ctx.ref_updates == []

    def test_single_ref_update_parsed(self, tmp_path: Path) -> None:
        stdin = "refs/heads/main abc123 refs/heads/main 000000"
        ctx = read_push_context(tmp_path, stdin_text=stdin)
        assert len(ctx.ref_updates) == 1
        local_ref, old, new = ctx.ref_updates[0]
        assert local_ref == "refs/heads/main"
        assert new == "abc123"

    def test_multiple_ref_updates_parsed(self, tmp_path: Path) -> None:
        stdin = (
            "refs/heads/main abc refs/heads/main 000\n"
            "refs/heads/feat bcd refs/heads/feat 001\n"
        )
        ctx = read_push_context(tmp_path, stdin_text=stdin)
        assert len(ctx.ref_updates) == 2
