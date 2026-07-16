"""Output redaction — remove secrets and credentials from check output.

Applies a fixed set of patterns targeting the most common secret shapes.
This is a best-effort filter; the primary defence is never logging secrets
in the first place.
"""

from __future__ import annotations

import re

# Patterns are applied in order; the first match wins.
# Each pattern replaces the sensitive portion with [REDACTED].
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # GitHub tokens (ghp_, ghs_, github_pat_, etc.)
    (re.compile(r"\bgh[ps]_[A-Za-z0-9_]{20,}"), "[REDACTED]"),
    # Bearer tokens
    (re.compile(r"\bBearer\s+\S{8,}", re.IGNORECASE), "Bearer [REDACTED]"),
    # password=, token=, api_key=, secret= patterns
    (
        re.compile(
            r"(password|token|api[_-]?key|secret|auth)\s*[=:]\s*\S+",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
]


def redact(output: str) -> str:
    """Return *output* with known secret patterns replaced by [REDACTED]."""
    if not output:
        return output
    result = output
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
