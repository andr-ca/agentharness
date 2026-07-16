"""GitHub review signals — fetch PR review and comment state."""

from __future__ import annotations

from dataclasses import dataclass

from agentharness.remote.github.models import PRState


@dataclass(frozen=True)
class ReviewSignals:
    """Aggregated review signals for a pull request."""

    pr_number: int
    head_sha: str
    approved: bool
    changes_requested: bool
    unresolved_thread_count: int
    passing_check_count: int
    failing_check_count: int

    @property
    def is_completion_eligible(self) -> bool:
        """Return True when all completion conditions are met."""
        return (
            self.approved
            and not self.changes_requested
            and self.unresolved_thread_count == 0
            and self.failing_check_count == 0
        )


def extract_signals(pr: PRState) -> ReviewSignals:
    """Extract structured review signals from a PRState."""
    return ReviewSignals(
        pr_number=pr.number,
        head_sha=pr.head_sha,
        approved=pr.review_decision == "APPROVED",
        changes_requested=pr.review_decision == "CHANGES_REQUESTED",
        unresolved_thread_count=pr.unresolved_threads,
        passing_check_count=len(pr.passing_checks),
        failing_check_count=len(pr.failing_checks),
    )
