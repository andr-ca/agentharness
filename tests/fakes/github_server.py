"""Fake GitHub server for testing — returns canned responses."""

from __future__ import annotations

import json
from typing import Any


class FakeGitHubServer:
    """Records calls and returns configured responses for testing."""

    def __init__(self) -> None:
        self._responses: dict[str, Any] = {}
        self.calls: list[str] = []

    def register(self, path: str, response: Any) -> None:
        self._responses[path] = response

    def get(self, path: str) -> Any:
        self.calls.append(path)
        if path not in self._responses:
            raise KeyError(f"No fake response registered for {path!r}")
        return self._responses[path]
