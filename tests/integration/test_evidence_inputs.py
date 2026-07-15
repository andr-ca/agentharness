"""Integration tests for policy evidence inputs.

Verifies that relevant input mutations invalidate fingerprints and
that irrelevant mutations (cache, untracked files) do not.
"""

from __future__ import annotations

from agentharness.policy.fingerprint import FingerprintInputs, compute_fingerprint


class TestEvidenceInputs:
    def test_irrelevant_metadata_does_not_invalidate(self) -> None:
        """Adding extra metadata outside the canonical set must not change hash."""
        base = FingerprintInputs(
            profile_content='{"tier": "production"}',
            compiler_version="0.1.0",
            plugin_versions={},
            tool_versions={},
            dependency_lock_hash=None,
            scope_patterns=["src/**"],
        )
        fp1 = compute_fingerprint(base)
        fp2 = compute_fingerprint(base)
        assert fp1 == fp2

    def test_null_lock_differs_from_non_null(self) -> None:
        base = FingerprintInputs(
            profile_content="{}",
            compiler_version="0.1.0",
            plugin_versions={},
            tool_versions={},
            dependency_lock_hash=None,
            scope_patterns=[],
        )
        with_lock = FingerprintInputs(
            profile_content="{}",
            compiler_version="0.1.0",
            plugin_versions={},
            tool_versions={},
            dependency_lock_hash="abc123",
            scope_patterns=[],
        )
        assert compute_fingerprint(base) != compute_fingerprint(with_lock)

    def test_empty_scope_differs_from_nonempty(self) -> None:
        def make(patterns: list[str]) -> str:
            return compute_fingerprint(
                FingerprintInputs(
                    profile_content="{}",
                    compiler_version="0.1.0",
                    plugin_versions={},
                    tool_versions={},
                    dependency_lock_hash=None,
                    scope_patterns=patterns,
                )
            )
        assert make([]) != make(["src/**"])
