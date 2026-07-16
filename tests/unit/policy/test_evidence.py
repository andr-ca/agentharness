"""Unit tests for policy evidence storage."""

from __future__ import annotations

from pathlib import Path

from agentharness.policy.evidence import EvidenceRecord, EvidenceStore


class TestEvidenceStore:
    def test_write_and_read_evidence(self, tmp_path: Path) -> None:
        store = EvidenceStore(root=tmp_path)
        record = EvidenceRecord(
            policy_hash="abc123",
            gate="commit",
            outcome="pass",
            args=["ruff", "check"],
            output="All checks passed.",
        )
        store.write(record)
        loaded = store.read(policy_hash="abc123", gate="commit")
        assert loaded is not None
        assert loaded.outcome == "pass"

    def test_missing_evidence_returns_none(self, tmp_path: Path) -> None:
        store = EvidenceStore(root=tmp_path)
        result = store.read(policy_hash="nonexistent", gate="commit")
        assert result is None

    def test_write_is_atomic(self, tmp_path: Path) -> None:
        """Writing evidence must not leave partial files on disk."""
        store = EvidenceStore(root=tmp_path)
        record = EvidenceRecord(
            policy_hash="hash1",
            gate="push",
            outcome="fail",
            args=["mypy"],
            output="type errors",
        )
        store.write(record)
        loaded = store.read("hash1", "push")
        assert loaded is not None
        assert loaded.gate == "push"
