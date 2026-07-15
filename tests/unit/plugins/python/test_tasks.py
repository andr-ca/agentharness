"""Unit tests for Python task runner detection.

Tests are fixture-driven. Detection is read-only and deterministic.
"""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.tasks import (
    TaskRunnerKind,
    detect_task_runners,
)

_HERE = Path(__file__).parent.parent.parent.parent
FIXTURES = _HERE / "fixtures" / "python" / "tasks"


class TestDetectTaskRunners:
    def test_tox_only(self) -> None:
        runners = detect_task_runners(FIXTURES / "tox-only")
        kinds = {r.kind for r in runners}
        assert TaskRunnerKind.TOX in kinds

    def test_nox_only(self) -> None:
        runners = detect_task_runners(FIXTURES / "nox-only")
        kinds = {r.kind for r in runners}
        assert TaskRunnerKind.NOX in kinds

    def test_make_only(self) -> None:
        runners = detect_task_runners(FIXTURES / "make-only")
        kinds = {r.kind for r in runners}
        assert TaskRunnerKind.MAKE in kinds

    def test_tox_and_nox_both_detected(self) -> None:
        runners = detect_task_runners(FIXTURES / "tox-and-nox")
        kinds = {r.kind for r in runners}
        assert TaskRunnerKind.TOX in kinds
        assert TaskRunnerKind.NOX in kinds

    def test_no_runner_returns_empty(self) -> None:
        runners = detect_task_runners(FIXTURES / "no-runner")
        assert runners == []

    def test_make_extracts_phony_targets(self) -> None:
        runners = detect_task_runners(FIXTURES / "make-only")
        make = next(r for r in runners if r.kind == TaskRunnerKind.MAKE)
        assert "test" in make.declared_targets
        assert "lint" in make.declared_targets

    def test_detection_is_deterministic(self) -> None:
        path = FIXTURES / "tox-and-nox"
        run1 = detect_task_runners(path)
        run2 = detect_task_runners(path)
        assert [r.kind for r in run1] == [r.kind for r in run2]

    def test_detection_does_not_mutate_project(self, tmp_path) -> None:
        before = set(tmp_path.rglob("*"))
        detect_task_runners(tmp_path)
        after = set(tmp_path.rglob("*"))
        assert before == after
