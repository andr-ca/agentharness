"""Byte-preserving marker-block insert/replace/remove for
harness-link.sh's existing-surface integration (see
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md).

Pure functions only — no filesystem I/O beyond atomic_write, no state,
no CLI. Orchestration lives in install_transaction.py.
"""
from __future__ import annotations

import hashlib


def detect_newline_style(text: str) -> str:
    """Return '\\r\\n' if the first newline in text is CRLF, else '\\n'.
    Defaults to '\\n' for text with no newlines at all."""
    idx = text.find("\n")
    if idx > 0 and text[idx - 1] == "\r":
        return "\r\n"
    return "\n"


def has_trailing_newline(text: str) -> bool:
    return text.endswith("\n") if text else False


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
