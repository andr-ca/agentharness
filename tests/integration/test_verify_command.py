"""Integration tests for the verify command and fail-closed behavior."""

from __future__ import annotations

from agentharness.policy.verifier import CheckOutcome, VerificationResult


class TestVerifyCommand:
    def test_strict_fail_blocks_gate(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.FAIL,
            args=["check"],
            output="failed",
            mode="strict",
        )
        assert result.is_blocking

    def test_warn_fail_does_not_block(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.FAIL,
            args=["check"],
            output="warning",
            mode="warn",
        )
        assert not result.is_blocking

    def test_grace_fail_does_not_block(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.FAIL,
            args=["check"],
            output="grace",
            mode="grace",
        )
        assert not result.is_blocking


class TestFailClosed:
    def test_error_outcome_blocks_in_strict_mode(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.ERROR,
            args=["missing-tool"],
            output="executable not found",
            mode="strict",
        )
        assert result.is_blocking

    def test_error_outcome_does_not_block_in_warn_mode(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.ERROR,
            args=["missing-tool"],
            output="executable not found",
            mode="warn",
        )
        assert not result.is_blocking
