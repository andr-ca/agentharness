"""Integration tests for PR reductions — code owner approvals and waivers."""

from __future__ import annotations

from agentharness.remote.github.models import PRState
from agentharness.remote.github.reviews import extract_signals


class TestReductions:
    def test_code_owner_approval_satisfies_review(self) -> None:
        pr = PRState(
            number=10,
            head_sha="sha1",
            is_draft=False,
            review_decision="APPROVED",
            unresolved_threads=0,
            passing_checks=["CI", "lint"],
            failing_checks=[],
        )
        signals = extract_signals(pr)
        assert signals.approved
        assert signals.is_completion_eligible

    def test_unapproved_pr_not_eligible(self) -> None:
        pr = PRState(
            number=11,
            head_sha="sha2",
            is_draft=False,
            review_decision=None,
            unresolved_threads=0,
            passing_checks=["CI"],
            failing_checks=[],
        )
        signals = extract_signals(pr)
        assert not signals.is_completion_eligible
