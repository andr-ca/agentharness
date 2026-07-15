"""Gate context types — canonical input types for each policy gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class GateEvent(StrEnum):
    COMMIT = "commit"
    PUSH = "push"
    CI = "ci"
    COMPLETION = "completion"


@dataclass(frozen=True)
class CommitContext:
    """Context supplied to the commit gate."""

    repo_root: Path
    staged_files: list[str]


@dataclass(frozen=True)
class PushContext:
    """Context supplied to the push gate.

    Each ref update is (local_ref, old_sha, new_sha).
    """

    repo_root: Path
    ref_updates: list[tuple[str, str, str]]


@dataclass(frozen=True)
class CIContext:
    """Context supplied to the CI gate."""

    event_name: str  # "pull_request", "push", "workflow_dispatch", etc.
    base_sha: str | None
    head_sha: str
    ref: str
