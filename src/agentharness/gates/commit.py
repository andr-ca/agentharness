"""Commit gate — read the Git index and validate staged content."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agentharness.gates.context import CommitContext


def read_commit_context(repo_root: Path) -> CommitContext:
    """Return the commit gate context from the current Git index.

    Reads staged files using `git diff --cached --name-only`.
    Returns an empty staged_files list if git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return CommitContext(repo_root=repo_root, staged_files=[])
        staged = [f for f in result.stdout.splitlines() if f.strip()]
        return CommitContext(repo_root=repo_root, staged_files=staged)
    except (FileNotFoundError, PermissionError):
        return CommitContext(repo_root=repo_root, staged_files=[])
