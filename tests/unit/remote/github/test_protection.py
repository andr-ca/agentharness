"""Unit tests for GitHub protection planning."""

from __future__ import annotations

from agentharness.remote.github.models import ProtectionPlan, ProtectionState
from agentharness.remote.github.protection import plan_protection


def _make_plan(approvals: int = 1) -> ProtectionPlan:
    return ProtectionPlan(
        branch="main",
        require_reviews=True,
        required_approvals=approvals,
        dismiss_stale_reviews=True,
        require_code_owner_reviews=True,
        required_contexts=["CI"],
    )


def _make_state(approvals: int = 1, protected: bool = True) -> ProtectionState:
    return ProtectionState(
        branch="main",
        is_protected=protected,
        required_approvals=approvals,
        dismiss_stale_reviews=True,
        require_code_owner_reviews=True,
        required_contexts=["CI"],
    )


class TestPlanProtection:
    def test_matching_state_matches_plan(self) -> None:
        plan = _make_plan()
        state = _make_state()
        result = plan_protection(plan, state)
        assert result.matches_plan

    def test_no_current_state_does_not_match(self) -> None:
        plan = _make_plan()
        result = plan_protection(plan, None)
        assert not result.matches_plan

    def test_insufficient_approvals_does_not_match(self) -> None:
        plan = _make_plan(approvals=2)
        state = _make_state(approvals=1)
        result = plan_protection(plan, state)
        assert not result.matches_plan

    def test_unprotected_does_not_match(self) -> None:
        plan = _make_plan()
        state = _make_state(protected=False)
        result = plan_protection(plan, state)
        assert not result.matches_plan
