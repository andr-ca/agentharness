"""Integration tests for PR completion gating."""

from __future__ import annotations

from agentharness.remote.github.completion import evaluate_completion
from agentharness.remote.github.reviews import ReviewSignals


class TestCompletion:
    def _ok(self, head: str = "sha1") -> ReviewSignals:
        return ReviewSignals(
            pr_number=1,
            head_sha=head,
            approved=True,
            changes_requested=False,
            unresolved_thread_count=0,
            passing_check_count=2,
            failing_check_count=0,
        )

    def test_matching_head_and_all_clear(self) -> None:
        decision = evaluate_completion(self._ok("sha1"), expected_head="sha1")
        assert decision.is_complete
        assert not decision.blocking_reasons

    def test_stale_head_sha_blocks(self) -> None:
        decision = evaluate_completion(self._ok("sha1"), expected_head="sha2")
        assert not decision.is_complete

    def test_blocking_reasons_describe_all_issues(self) -> None:
        signals = ReviewSignals(
            pr_number=1,
            head_sha="old",
            approved=False,
            changes_requested=True,
            unresolved_thread_count=3,
            passing_check_count=0,
            failing_check_count=1,
        )
        decision = evaluate_completion(signals, expected_head="expected")
        assert len(decision.blocking_reasons) >= 4
