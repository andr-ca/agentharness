"""Push gate — parse Git ref update stdin and validate outgoing revisions."""

from __future__ import annotations

import sys
from pathlib import Path

from agentharness.gates.context import PushContext


def read_push_context(repo_root: Path, stdin_text: str | None = None) -> PushContext:
    """Parse Git's pre-push stdin into a PushContext.

    Git passes lines of the form:
        <local-ref> <local-sha> <remote-ref> <remote-sha>

    We record (local_ref, old_sha, new_sha) for each update.
    """
    text = stdin_text if stdin_text is not None else sys.stdin.read()
    updates: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            local_ref, local_sha, _remote_ref, remote_sha = parts[:4]
            updates.append((local_ref, remote_sha, local_sha))
    return PushContext(repo_root=repo_root, ref_updates=updates)
