"""Policy verifier — executes checks and returns typed results.

The verifier never uses shell=True. All command execution goes through
subprocess argument arrays. Plugin exceptions and missing executables are
caught and converted to typed ERROR outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

_MAX_OUTPUT_BYTES = 8192


class CheckOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class VerificationResult:
    """The outcome of executing a single policy requirement check."""

    outcome: CheckOutcome
    args: list[str]
    output: str
    mode: str = "strict"

    @property
    def is_blocking(self) -> bool:
        """True if this result must prevent the gate from passing."""
        if self.mode in ("warn", "grace"):
            return False
        return self.outcome in (CheckOutcome.FAIL, CheckOutcome.ERROR)


class VerificationError(RuntimeError):
    """Raised when the verifier encounters an unrecoverable error."""


def verify_requirement(
    check_fn: Callable[..., int],
    args: list[str],
    mode: str = "strict",
    output: str = "",
) -> VerificationResult:
    """Execute *check_fn* and return a typed VerificationResult.

    *check_fn* must return an exit code (0 = pass, non-zero = fail).
    FileNotFoundError is treated as a missing-executable ERROR.
    Any other exception is also converted to ERROR.
    The output is capped at _MAX_OUTPUT_BYTES characters.
    """
    capped = output[:_MAX_OUTPUT_BYTES]
    try:
        exit_code = check_fn(*args)
        outcome = CheckOutcome.PASS if exit_code == 0 else CheckOutcome.FAIL
    except FileNotFoundError:
        outcome = CheckOutcome.ERROR
        capped = "executable not found"
    except Exception:  # noqa: BLE001
        outcome = CheckOutcome.ERROR
        capped = "unexpected error during check"

    return VerificationResult(
        outcome=outcome,
        args=args,
        output=capped,
        mode=mode,
    )
