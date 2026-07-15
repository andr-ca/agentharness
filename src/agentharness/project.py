"""Project context — reads project-level state for bootstrap calculations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectContext:
    """Immutable snapshot of the project directory relevant to bootstrap.

    root: absolute path to the project root (the directory containing
          `.git/` or the worktree checkout).
    """

    root: Path

    @classmethod
    def from_cwd(cls) -> "ProjectContext":
        """Locate the project root by searching upward from cwd."""
        candidate = Path.cwd().resolve()
        while candidate != candidate.parent:
            if (candidate / ".git").exists():
                return cls(root=candidate)
            candidate = candidate.parent
        raise RuntimeError("No .git directory found from cwd upward")
