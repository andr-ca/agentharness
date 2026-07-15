"""Unit tests for Python typing tool detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.typing import (
    TypingToolKind,
    detect_typing_tools,
)

_HERE = Path(__file__).parent.parent.parent.parent
FIXTURES = _HERE / "fixtures" / "python" / "quality"


class TestDetectTypingTools:
    def test_mypy_only(self) -> None:
        tools = detect_typing_tools(FIXTURES / "mypy-only")
        kinds = {t.kind for t in tools}
        assert TypingToolKind.MYPY in kinds

    def test_ruff_and_mypy(self) -> None:
        """Only mypy is a typing tool; ruff is linting."""
        tools = detect_typing_tools(FIXTURES / "ruff-and-mypy")
        kinds = {t.kind for t in tools}
        assert TypingToolKind.MYPY in kinds

    def test_no_typing_tools_returns_empty(self) -> None:
        tools = detect_typing_tools(FIXTURES / "no-quality-tools")
        assert tools == []

    def test_ruff_only_has_no_typing_tools(self) -> None:
        tools = detect_typing_tools(FIXTURES / "ruff-only")
        assert tools == []

    def test_detection_is_deterministic(self) -> None:
        path = FIXTURES / "mypy-only"
        run1 = detect_typing_tools(path)
        run2 = detect_typing_tools(path)
        assert [t.kind for t in run1] == [t.kind for t in run2]
