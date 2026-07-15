"""Integration tests for CI gate context and policy integrity."""

from __future__ import annotations

from agentharness.gates.ci import read_ci_context
from agentharness.policy.integrity import verify_policy_integrity


class TestCIGate:
    def test_pr_context_has_base_sha(self) -> None:
        ctx = read_ci_context(
            event_name="pull_request",
            head_sha="head123",
            ref="refs/pull/1/merge",
            base_sha="base456",
        )
        assert ctx.base_sha == "base456"
        assert ctx.event_name == "pull_request"

    def test_push_context_has_no_base(self) -> None:
        ctx = read_ci_context(
            event_name="push",
            head_sha="head123",
            ref="refs/heads/main",
        )
        assert ctx.base_sha is None


class TestBasePolicy:
    def test_matching_hash_is_intact(self) -> None:
        import hashlib
        content = '{"tier": "production"}'
        h = hashlib.sha256(content.encode()).hexdigest()
        result = verify_policy_integrity(content, h)
        assert result.is_intact

    def test_mismatched_hash_fails(self) -> None:
        result = verify_policy_integrity('{"tier": "internal"}', "wrong_hash")
        assert not result.is_intact

    def test_no_expected_hash_fails(self) -> None:
        result = verify_policy_integrity("any content", None)
        assert not result.is_intact
