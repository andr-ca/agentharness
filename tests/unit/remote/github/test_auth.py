"""Unit tests for GitHub auth."""

from __future__ import annotations

import pytest

from agentharness.remote.github.auth import AuthError, get_token, redact_token


class TestGetToken:
    def test_reads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "abc123")
        assert get_token("MY_TOKEN") == "abc123"

    def test_missing_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(AuthError):
            get_token("GITHUB_TOKEN")


class TestRedactToken:
    def test_redacts_token(self) -> None:
        assert "secret" not in redact_token("value=secret", "secret")

    def test_no_op_empty(self) -> None:
        assert redact_token("text", "") == "text"
