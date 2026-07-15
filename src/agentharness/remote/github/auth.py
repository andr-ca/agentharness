"""GitHub authentication — token validation and redaction."""

from __future__ import annotations

import os


class AuthError(RuntimeError):
    """Raised when GitHub credentials are missing or invalid."""


def get_token(env_var: str = "GITHUB_TOKEN") -> str:
    """Read the GitHub token from the environment.

    Raises AuthError if the variable is absent or empty.
    Never includes the token value in error messages.
    """
    token = os.environ.get(env_var, "").strip()
    if not token:
        raise AuthError(
            f"GitHub token not found in ${env_var}. "
            "Set the environment variable before running."
        )
    return token


def redact_token(text: str, token: str) -> str:
    """Replace any occurrence of *token* in *text* with [REDACTED]."""
    if not token:
        return text
    return text.replace(token, "[REDACTED]")
