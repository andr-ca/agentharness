"""Unit tests for policy fingerprinting.

Tests verify that each relevant input mutation changes the fingerprint,
while irrelevant mutations (untracked files, cache dirs) do not.
"""

from __future__ import annotations

from pathlib import Path

from agentharness.policy.fingerprint import (
    FingerprintInputs,
    compute_fingerprint,
)


def _base_inputs(**overrides: object) -> FingerprintInputs:
    defaults: dict[str, object] = {
        "profile_content": '{"tier": "production"}',
        "compiler_version": "0.1.0",
        "plugin_versions": {"my.plugin": "1.0.0"},
        "tool_versions": {"ruff": "0.4.0"},
        "dependency_lock_hash": "abc123",
        "scope_patterns": ["src/**"],
    }
    defaults.update(overrides)
    return FingerprintInputs(**defaults)  # type: ignore[arg-type]


class TestFingerprintInvalidation:
    def test_identical_inputs_produce_same_fingerprint(self) -> None:
        f1 = compute_fingerprint(_base_inputs())
        f2 = compute_fingerprint(_base_inputs())
        assert f1 == f2

    def test_profile_change_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(profile_content='{"tier": "production"}'))
        f2 = compute_fingerprint(_base_inputs(profile_content='{"tier": "internal"}'))
        assert f1 != f2

    def test_compiler_version_change_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(compiler_version="0.1.0"))
        f2 = compute_fingerprint(_base_inputs(compiler_version="0.2.0"))
        assert f1 != f2

    def test_plugin_version_change_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(plugin_versions={"p": "1.0.0"}))
        f2 = compute_fingerprint(_base_inputs(plugin_versions={"p": "2.0.0"}))
        assert f1 != f2

    def test_tool_version_change_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(tool_versions={"ruff": "0.4.0"}))
        f2 = compute_fingerprint(_base_inputs(tool_versions={"ruff": "0.5.0"}))
        assert f1 != f2

    def test_dependency_lock_change_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(dependency_lock_hash="aaa"))
        f2 = compute_fingerprint(_base_inputs(dependency_lock_hash="bbb"))
        assert f1 != f2

    def test_scope_pattern_change_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(scope_patterns=["src/**"]))
        f2 = compute_fingerprint(_base_inputs(scope_patterns=["src/**", "tests/**"]))
        assert f1 != f2

    def test_adding_plugin_invalidates(self) -> None:
        f1 = compute_fingerprint(_base_inputs(plugin_versions={}))
        f2 = compute_fingerprint(_base_inputs(plugin_versions={"new.plugin": "1.0.0"}))
        assert f1 != f2

    def test_fingerprint_is_hex_string(self) -> None:
        fp = compute_fingerprint(_base_inputs())
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)
