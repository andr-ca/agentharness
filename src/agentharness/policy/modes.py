"""Policy mode aggregation — collect per-requirement results and determine
whether a gate is passing or blocking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PolicyMode(StrEnum):
    STRICT = "strict"
    WARN = "warn"
    GRACE = "grace"


@dataclass
class _RequirementRecord:
    requirement_id: str
    mode: PolicyMode
    passed: bool


class ModeAggregator:
    """Accumulates per-requirement pass/fail records and computes gate status.

    A gate passes only when all STRICT requirements pass.
    WARN and GRACE failures are recorded but do not block the gate.
    """

    def __init__(self) -> None:
        self._records: list[_RequirementRecord] = []

    def record(self, requirement_id: str, mode: PolicyMode, passed: bool) -> None:
        self._records.append(
            _RequirementRecord(requirement_id=requirement_id, mode=mode, passed=passed)
        )

    def is_gate_passing(self) -> bool:
        """Return True only when no STRICT requirement has failed."""
        return all(
            r.passed
            for r in self._records
            if r.mode == PolicyMode.STRICT
        )

    def get_failures(self) -> list[str]:
        """Return all requirement IDs that failed, regardless of mode."""
        return [r.requirement_id for r in self._records if not r.passed]
