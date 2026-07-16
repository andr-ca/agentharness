"""Unit tests for output redaction."""

from __future__ import annotations

from agentharness.policy.redaction import redact


class TestRedaction:
    def test_token_redacted(self) -> None:
        output = "Authorization: Bearer ghp_12345abcde"
        result = redact(output)
        assert "ghp_12345abcde" not in result
        assert "[REDACTED]" in result

    def test_password_pattern_redacted(self) -> None:
        output = "password=supersecret123"
        result = redact(output)
        assert "supersecret123" not in result

    def test_clean_output_unchanged(self) -> None:
        output = "All checks passed. No issues found."
        result = redact(output)
        assert result == output

    def test_empty_output_unchanged(self) -> None:
        assert redact("") == ""

    def test_multiple_secrets_all_redacted(self) -> None:
        output = "token=abc123\napi_key=xyz789"
        result = redact(output)
        assert "abc123" not in result
        assert "xyz789" not in result
