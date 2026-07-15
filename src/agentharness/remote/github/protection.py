"""GitHub branch protection — read, plan, apply, and verify."""

from __future__ import annotations

from dataclasses import dataclass

from agentharness.remote.github.models import ProtectionPlan, ProtectionState


@dataclass(frozen=True)
class ReconcileResult:
    """The result of a protection reconciliation operation."""

    plan: ProtectionPlan
    applied: bool
    current_state: ProtectionState | None
    matches_plan: bool


def plan_protection(
    desired: ProtectionPlan,
    current: ProtectionState | None,
) -> ReconcileResult:
    """Compute whether the desired protection matches the current state.

    Returns a ReconcileResult describing whether the plan needs to be applied.
    """
    if current is None:
        return ReconcileResult(
            plan=desired,
            applied=False,
            current_state=None,
            matches_plan=False,
        )

    matches = (
        current.is_protected
        and current.required_approvals >= desired.required_approvals
        and current.dismiss_stale_reviews == desired.dismiss_stale_reviews
        and current.require_code_owner_reviews
        >= desired.require_code_owner_reviews
        and all(ctx in current.required_contexts for ctx in desired.required_contexts)
    )
    return ReconcileResult(
        plan=desired,
        applied=False,
        current_state=current,
        matches_plan=matches,
    )
