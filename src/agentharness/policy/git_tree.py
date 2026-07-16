"""Git tree utilities for fingerprinting staged content.

Provides stable, content-addressed hashing of the Git index state
without reading from the working tree.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def hash_git_index(repo_root: Path) -> str:
    """Return a hash of the current Git index (staged files).

    Uses `git ls-files --stage` to enumerate staged blobs by their
    Git object IDs.  This reflects the tree that would be committed,
    not the working-tree state.

    Returns an empty-tree sentinel hash if git is unavailable or the
    directory is not a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--stage"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return _empty_tree_hash()
        return hashlib.sha256(result.stdout.encode()).hexdigest()
    except (FileNotFoundError, PermissionError):
        return _empty_tree_hash()


def _empty_tree_hash() -> str:
    """SHA-256 of an empty string — used as a sentinel for missing git context."""
    return hashlib.sha256(b"").hexdigest()
