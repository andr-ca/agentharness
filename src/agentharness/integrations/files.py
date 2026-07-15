"""Generated file ownership and managed block writer."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum


class MergeStrategy(StrEnum):
    CREATE = "create"
    MANAGED_BLOCK = "managed-block"
    STRUCTURED_MERGE = "structured-merge"
    PROPOSAL_ONLY = "proposal-only"


@dataclass(frozen=True)
class FileOwnership:
    """Declares how a file should be created or updated."""

    path: str
    strategy: MergeStrategy
    content_hash: str | None = None


def plan_create(path: str, content: bytes) -> FileOwnership:
    """Plan creating a new file with *content*."""
    return FileOwnership(
        path=path,
        strategy=MergeStrategy.CREATE,
        content_hash=hashlib.sha256(content).hexdigest(),
    )


def plan_managed_block(path: str, block_id: str, content: bytes) -> FileOwnership:
    """Plan inserting/updating a managed block within an existing file."""
    return FileOwnership(
        path=path,
        strategy=MergeStrategy.MANAGED_BLOCK,
        content_hash=hashlib.sha256(f"{block_id}:{content.decode()}".encode()).hexdigest(),
    )
