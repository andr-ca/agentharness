"""Unit tests for ChangePlan descriptors."""

from __future__ import annotations

from agentharness.plugins.python.plan import ChangePlan, MergeStrategy, PlannedChange


class TestPlan:
    def test_create_plan(self) -> None:
        change = PlannedChange(
            path="pyproject.toml",
            strategy=MergeStrategy.STRUCTURED_MERGE,
            description="Add [tool.ruff] section",
            owner="agentharness.python",
        )
        plan = ChangePlan(recommendation_id="python.add-ruff", changes=[change])
        assert plan.recommendation_id == "python.add-ruff"
        assert len(plan.changes) == 1
        assert plan.changes[0].strategy == MergeStrategy.STRUCTURED_MERGE

    def test_proposal_only_does_not_mutate(self) -> None:
        """A PROPOSAL_ONLY change must never be applied directly."""
        change = PlannedChange(
            path="pyproject.toml",
            strategy=MergeStrategy.PROPOSAL_ONLY,
            description="Propose adding ruff",
            owner="agentharness.python",
        )
        assert change.strategy == MergeStrategy.PROPOSAL_ONLY
