"""Unit tests for Python logging detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.logging import LoggingKind, detect_logging

_HERE = Path(__file__).parent.parent.parent.parent
FIXTURES = _HERE / "fixtures" / "python" / "runtime-quality"


class TestDetectLogging:
    def test_structlog_project(self) -> None:
        result = detect_logging(FIXTURES / "structlog-project")
        assert result.kind == LoggingKind.STRUCTLOG

    def test_stdlib_fallback(self) -> None:
        result = detect_logging(FIXTURES / "stdlib-logging")
        assert result.kind == LoggingKind.STDLIB

    def test_no_pyproject_returns_absent(self) -> None:
        result = detect_logging(FIXTURES / "no-logging")
        assert result.kind == LoggingKind.ABSENT

    def test_detection_is_deterministic(self) -> None:
        r1 = detect_logging(FIXTURES / "structlog-project")
        r2 = detect_logging(FIXTURES / "structlog-project")
        assert r1.kind == r2.kind
