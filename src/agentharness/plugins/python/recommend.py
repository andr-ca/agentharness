"""Python plugin recommendations — compose findings into prioritised proposals.

Recommendations are optional unless a mandatory baseline is already present.
Detected mandatory baselines are preserved; incompatible stacks produce
explicit questions rather than silent choices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Impact(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Cost(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Recommendation:
    """A single, stable, optionally-actionable recommendation."""

    id: str                        # stable dot-separated ID
    summary: str                   # one-line human description
    impact: Impact
    cost: Cost
    rationale: str                 # why this recommendation is made
    optional: bool = True          # False = already enforced; True = suggestion


def compose_recommendations(
    findings: list[dict[str, str]],
) -> list[Recommendation]:
    """Turn raw findings into a sorted, stable recommendation list.

    Sorting is by (impact descending, cost ascending, id ascending) so
    callers see the highest-value, lowest-cost items first.
    """
    recs = []
    for f in findings:
        rec = Recommendation(
            id=f["id"],
            summary=f["summary"],
            impact=Impact(f.get("impact", Impact.MEDIUM)),
            cost=Cost(f.get("cost", Cost.MEDIUM)),
            rationale=f.get("rationale", ""),
            optional=f.get("optional", "true").lower() != "false",
        )
        recs.append(rec)

    _impact_order = {Impact.HIGH: 0, Impact.MEDIUM: 1, Impact.LOW: 2}
    _cost_order = {Cost.LOW: 0, Cost.MEDIUM: 1, Cost.HIGH: 2}
    return sorted(
        recs,
        key=lambda r: (_impact_order[r.impact], _cost_order[r.cost], r.id),
    )
