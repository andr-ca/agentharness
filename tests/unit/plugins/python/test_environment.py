"""Unit tests for Python environment detection.

Tests are fixture-driven — each fixture directory represents one project
configuration. Detection is read-only and produces no side effects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentharness.plugins.python.environment import (
    EnvironmentKind,
    PythonEnvironment,
    detect_environment,
)

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "python" / "environment"


class TestDetectEnvironment:
    def test_pyproject_only(self) -> None:
        env = detect_environment(FIXTURES / "pyproject-only")
        assert env.kind == EnvironmentKind.PYPROJECT
        assert env.has_lock_file is False

    def test_setup_py_only(self) -> None:
        env = detect_environment(FIXTURES / "setup-py-only")
        assert env.kind == EnvironmentKind.SETUP_PY

    def test_requirements_only(self) -> None:
        env = detect_environment(FIXTURES / "requirements-only")
        assert env.kind == EnvironmentKind.REQUIREMENTS
        assert env.has_lock_file is False

    def test_uv_project_detects_lock_file(self) -> None:
        env = detect_environment(FIXTURES / "uv-project")
        assert env.kind == EnvironmentKind.PYPROJECT
        assert env.lock_file_name == "uv.lock"
        assert env.has_lock_file is True

    def test_poetry_project_detects_lock_file(self) -> None:
        env = detect_environment(FIXTURES / "poetry-project")
        assert env.kind == EnvironmentKind.PYPROJECT
        assert env.lock_file_name == "poetry.lock"
        assert env.has_lock_file is True

    def test_pipenv_project(self) -> None:
        env = detect_environment(FIXTURES / "pipenv-project")
        assert env.kind == EnvironmentKind.PIPENV

    def test_no_python_marker_returns_unknown(self) -> None:
        env = detect_environment(FIXTURES / "no-python-marker")
        assert env.kind == EnvironmentKind.UNKNOWN

    def test_nonexistent_directory_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            detect_environment(FIXTURES / "nonexistent-fixture")

    def test_detection_is_deterministic(self) -> None:
        """Running detection twice on the same fixture yields identical results."""
        path = FIXTURES / "pyproject-only"
        env1 = detect_environment(path)
        env2 = detect_environment(path)
        assert env1.kind == env2.kind
        assert env1.has_lock_file == env2.has_lock_file

    def test_detection_does_not_mutate_project(self, tmp_path: Path) -> None:
        """Detection must not write any files to the project directory."""
        before = set(tmp_path.rglob("*"))
        detect_environment(tmp_path)
        after = set(tmp_path.rglob("*"))
        assert before == after
