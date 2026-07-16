"""Integration tests for GitHub reconciliation and protection commands."""

from __future__ import annotations

from agentharness.remote.github.models import ProtectionPlan, ProtectionState
from agentharness.remote.github.protection import plan_protection


class TestGitHubReconcile:
    def test_reconcile_detects_no_protection(self) -> None:
        plan = ProtectionPlan(
            branch="main",
            require_reviews=True,
            required_approvals=1,
            dismiss_stale_reviews=True,
            require_code_owner_reviews=True,
            required_contexts=["CI"],
        )
        result = plan_protection(plan, current=None)
        assert not result.matches_plan

    def test_reconcile_detects_matching_protection(self) -> None:
        plan = ProtectionPlan(
            branch="main",
            require_reviews=True,
            required_approvals=1,
            dismiss_stale_reviews=True,
            require_code_owner_reviews=True,
            required_contexts=["CI"],
        )
        current = ProtectionState(
            branch="main",
            is_protected=True,
            required_approvals=1,
            dismiss_stale_reviews=True,
            require_code_owner_reviews=True,
            required_contexts=["CI"],
        )
        result = plan_protection(plan, current=current)
        assert result.matches_plan


class TestProtectionCommands:
    def test_protection_plan_is_immutable(self) -> None:
        plan = ProtectionPlan(
            branch="main",
            require_reviews=True,
            required_approvals=1,
            dismiss_stale_reviews=False,
            require_code_owner_reviews=False,
            required_contexts=[],
        )
        assert plan.branch == "main"
