"""Managed block inserter — maintains a delimited section in a file."""

from __future__ import annotations

_BLOCK_START = "# BEGIN AGENTHARNESS-MANAGED: {id}"
_BLOCK_END = "# END AGENTHARNESS-MANAGED: {id}"


def apply_managed_block(existing: str, block_id: str, new_content: str) -> str:
    """Insert or replace a managed block in *existing*.

    If the block markers are already present, the content between them is
    replaced.  Otherwise the block is appended.
    """
    start_marker = _BLOCK_START.format(id=block_id)
    end_marker = _BLOCK_END.format(id=block_id)

    if start_marker in existing:
        start_idx = existing.index(start_marker)
        end_idx = existing.index(end_marker, start_idx) + len(end_marker)
        block = f"{start_marker}\n{new_content}\n{end_marker}"
        return existing[:start_idx] + block + existing[end_idx:]

    block = f"\n{start_marker}\n{new_content}\n{end_marker}\n"
    return existing + block
