"""Unit tests for the policy verifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agentharness.policy.verifier import (
    CheckOutcome,
    VerificationError,
    VerificationResult,
    verify_requirement,
)


class TestVerifyRequirement:
    def test_passing_check_returns_pass(self) -> None:
        check = MagicMock(return_value=0)
        result = verify_requirement(check, args=["--check"])
        assert result.outcome == CheckOutcome.PASS

    def test_failing_check_returns_fail(self) -> None:
        check = MagicMock(return_value=1)
        result = verify_requirement(check, args=["--check"])
        assert result.outcome == CheckOutcome.FAIL

    def test_missing_executable_returns_error(self) -> None:
        def raise_fnf(*args: object, **kwargs: object) -> int:
            raise FileNotFoundError("not found")

        result = verify_requirement(raise_fnf, args=["--check"])
        assert result.outcome == CheckOutcome.ERROR

    def test_result_includes_args(self) -> None:
        check = MagicMock(return_value=0)
        result = verify_requirement(check, args=["ruff", "check", "src/"])
        assert result.args == ["ruff", "check", "src/"]

    def test_output_is_capped(self) -> None:
        """stdout/stderr in the result must not exceed a reasonable size."""
        check = MagicMock(return_value=0)
        result = verify_requirement(check, args=[], output="x" * 100_000)
        assert len(result.output) <= 8192


class TestCheckOutcome:
    def test_strict_fail_is_blocking(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.FAIL,
            args=["ruff"],
            output="errors found",
            mode="strict",
        )
        assert result.is_blocking

    def test_warn_fail_is_not_blocking(self) -> None:
        result = VerificationResult(
            outcome=CheckOutcome.FAIL,
            args=["ruff"],
            output="errors found",
            mode="warn",
        )
        assert not result.is_blocking

    def test_pass_is_never_blocking(self) -> None:
        for mode in ("strict", "warn", "grace"):
            result = VerificationResult(
                outcome=CheckOutcome.PASS,
                args=["ruff"],
                output="ok",
                mode=mode,
            )
            assert not result.is_blocking
