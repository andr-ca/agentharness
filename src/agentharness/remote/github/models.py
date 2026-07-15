"""Typed GitHub API models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubRepo:
    """Minimal repository identity."""

    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class ProtectionPlan:
    """A computed plan for branch protection changes."""

    branch: str
    require_reviews: bool
    required_approvals: int
    dismiss_stale_reviews: bool
    require_code_owner_reviews: bool
    required_contexts: list[str]


@dataclass(frozen=True)
class ProtectionState:
    """The current protection state read back from GitHub."""

    branch: str
    is_protected: bool
    required_approvals: int
    dismiss_stale_reviews: bool
    require_code_owner_reviews: bool
    required_contexts: list[str]


@dataclass(frozen=True)
class PRState:
    """The review and check state of a pull request."""

    number: int
    head_sha: str
    is_draft: bool
    review_decision: str | None  # "APPROVED", "CHANGES_REQUESTED", None
    unresolved_threads: int
    passing_checks: list[str]
    failing_checks: list[str]
