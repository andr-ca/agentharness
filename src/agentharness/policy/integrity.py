"""Policy integrity verification — confirm the policy source has not been tampered.

Checks that the deployed policy comes from the base commit for PRs, not
from the head commit where attacker-controlled code could spoof results.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrityResult:
    """The outcome of a policy integrity check."""

    is_intact: bool
    base_sha: str | None
    policy_hash: str | None
    reason: str


def verify_policy_integrity(
    policy_content: str,
    expected_hash: str | None,
) -> IntegrityResult:
    """Verify that *policy_content* matches *expected_hash*.

    If *expected_hash* is None, integrity cannot be verified and the
    check is marked not-intact in strict mode.
    """
    if expected_hash is None:
        return IntegrityResult(
            is_intact=False,
            base_sha=None,
            policy_hash=None,
            reason=(
                "no expected hash — cannot verify integrity without a base reference"
            ),
        )

    actual = hashlib.sha256(policy_content.encode()).hexdigest()
    if actual != expected_hash:
        return IntegrityResult(
            is_intact=False,
            base_sha=None,
            policy_hash=actual,
            reason=(
            f"policy hash mismatch: got {actual!r}, "
            f"expected {expected_hash!r}"
        ),
        )

    return IntegrityResult(
        is_intact=True,
        base_sha=None,
        policy_hash=actual,
        reason="policy content matches expected hash",
    )
