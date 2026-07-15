"""Integration tests for fail-closed behavior."""

from __future__ import annotations

from agentharness.policy.verifier import CheckOutcome, VerificationResult, verify_requirement


class TestFailClosed:
    def test_missing_tool_fails_closed_in_strict_mode(self) -> None:
        def raise_fnf(*args: object, **kwargs: object) -> int:
            raise FileNotFoundError("tool not on PATH")

        result = verify_requirement(raise_fnf, args=["missing-tool"], mode="strict")
        assert result.outcome == CheckOutcome.ERROR
        assert result.is_blocking

    def test_missing_tool_warns_in_warn_mode(self) -> None:
        def raise_fnf(*args: object, **kwargs: object) -> int:
            raise FileNotFoundError("tool not on PATH")

        result = verify_requirement(raise_fnf, args=["missing-tool"], mode="warn")
        assert result.outcome == CheckOutcome.ERROR
        assert not result.is_blocking
