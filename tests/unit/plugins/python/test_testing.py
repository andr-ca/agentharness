"""Unit tests for Python test framework detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.testing import (
    FrameworkKind,
    detect_test_frameworks,
)

_HERE = Path(__file__).parent.parent.parent.parent
FIXTURES = _HERE / "fixtures" / "python" / "quality"


class TestDetectTestFrameworks:
    def test_pytest_config(self) -> None:
        frameworks = detect_test_frameworks(FIXTURES / "pytest-only")
        kinds = {f.kind for f in frameworks}
        assert FrameworkKind.PYTEST in kinds

    def test_no_test_config_returns_empty(self) -> None:
        frameworks = detect_test_frameworks(FIXTURES / "no-quality-tools")
        assert frameworks == []

    def test_ruff_config_has_no_test_framework(self) -> None:
        frameworks = detect_test_frameworks(FIXTURES / "ruff-only")
        assert frameworks == []

    def test_detection_is_deterministic(self) -> None:
        path = FIXTURES / "pytest-only"
        run1 = detect_test_frameworks(path)
        run2 = detect_test_frameworks(path)
        assert [f.kind for f in run1] == [f.kind for f in run2]

    def test_detection_does_not_mutate_project(self, tmp_path) -> None:
        before = set(tmp_path.rglob("*"))
        detect_test_frameworks(tmp_path)
        after = set(tmp_path.rglob("*"))
        assert before == after
