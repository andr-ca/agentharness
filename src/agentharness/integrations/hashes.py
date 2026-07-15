"""Generator hashes — stable content hashes for dispatched template files."""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of *path*'s contents."""
    if not path.exists():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_template(template_name: str, harness_root: Path) -> str:
    """Return the hash of a named template file."""
    template = harness_root / "templates" / template_name
    return hash_file(template)
