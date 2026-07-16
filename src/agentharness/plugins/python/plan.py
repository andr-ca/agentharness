"""Generated change plan descriptors.

Plans describe file changes without executing them.  The apply/rollback
cycle is handled by the transaction system (bootstrap/transaction.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MergeStrategy(StrEnum):
    CREATE = "create"              # create a new file
    MANAGED_BLOCK = "managed-block"  # insert/update a delimited block
    STRUCTURED_MERGE = "structured-merge"  # merge structured config
    PROPOSAL_ONLY = "proposal-only"  # describe only, don't write


@dataclass(frozen=True)
class PlannedChange:
    """A single planned file change."""

    path: str
    strategy: MergeStrategy
    description: str
    owner: str  # plugin_id or "core"


@dataclass(frozen=True)
class ChangePlan:
    """A set of related planned changes produced by a recommendation."""

    recommendation_id: str
    changes: list[PlannedChange]
