"""Typed GitHub API client — HTTP boundary with token redaction."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from agentharness.remote.github.auth import redact_token

_GITHUB_API = "https://api.github.com"


class APIError(RuntimeError):
    """Raised when the GitHub API returns an error."""


class RateLimitError(APIError):
    """Raised when the API rate limit is exceeded (429)."""


class GitHubClient:
    """Minimal GitHub REST API client.

    *token* is never included in error messages or logs.
    """

    def __init__(self, token: str, base_url: str = _GITHUB_API) -> None:
        self._token = token
        self._base = base_url.rstrip("/")

    def get(self, path: str) -> Any:
        """GET *path* from the API and return the parsed JSON."""
        url = f"{self._base}{path}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimitError("GitHub API rate limit exceeded") from e
            body = e.read().decode(errors="replace")
            safe_body = redact_token(body, self._token)
            raise APIError(
                f"GitHub API error {e.code} for {path}: {safe_body}"
            ) from e
        except urllib.error.URLError as e:
            raise APIError(f"Network error for {path}: {e.reason}") from e
