"""Verification helpers — confirm that applied recommendations are active."""

from __future__ import annotations

from pathlib import Path


def verify_file_exists(root: Path, relative_path: str) -> bool:
    """Return True if *relative_path* exists under *root*."""
    return (root / relative_path).exists()


def verify_config_key(
    root: Path,
    relative_path: str,
    expected_key: str,
) -> bool:
    """Return True if *expected_key* appears anywhere in the named file."""
    p = root / relative_path
    if not p.exists():
        return False
    return expected_key in p.read_text(encoding="utf-8", errors="replace")
