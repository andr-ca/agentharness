"""Python environment detection.

Detects the project's dependency management approach from on-disk files.
Detection is read-only and has no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class EnvironmentKind(StrEnum):
    """The detected dependency management approach."""

    PYPROJECT = "pyproject"        # pyproject.toml present
    SETUP_PY = "setup_py"          # setup.py (legacy)
    REQUIREMENTS = "requirements"  # requirements.txt only
    PIPENV = "pipenv"              # Pipfile + Pipfile.lock
    UNKNOWN = "unknown"            # no recognisable marker found


@dataclass(frozen=True)
class PythonEnvironment:
    """The result of detecting a Python project's environment."""

    kind: EnvironmentKind
    has_lock_file: bool = False
    lock_file_name: str | None = None
    material_files: list[str] = field(default_factory=list)


def detect_environment(root: Path) -> PythonEnvironment:
    """Detect the Python environment in *root*.

    Raises FileNotFoundError if *root* does not exist.
    Returns PythonEnvironment(kind=UNKNOWN) if no Python marker is found.

    This function is pure and read-only — it never writes any file.
    """
    if not root.exists():
        raise FileNotFoundError(f"Project directory not found: {root}")

    # Pipenv: Pipfile takes precedence over pyproject if it's the primary tool
    if (root / "Pipfile").exists():
        lock = (root / "Pipfile.lock").exists()
        return PythonEnvironment(
            kind=EnvironmentKind.PIPENV,
            has_lock_file=lock,
            lock_file_name="Pipfile.lock" if lock else None,
            material_files=["Pipfile"] + (["Pipfile.lock"] if lock else []),
        )

    # pyproject.toml (uv, Poetry, or plain PEP 517)
    if (root / "pyproject.toml").exists():
        for lock_name in ("uv.lock", "poetry.lock"):
            if (root / lock_name).exists():
                return PythonEnvironment(
                    kind=EnvironmentKind.PYPROJECT,
                    has_lock_file=True,
                    lock_file_name=lock_name,
                    material_files=["pyproject.toml", lock_name],
                )
        return PythonEnvironment(
            kind=EnvironmentKind.PYPROJECT,
            has_lock_file=False,
            material_files=["pyproject.toml"],
        )

    # Legacy setup.py
    if (root / "setup.py").exists():
        return PythonEnvironment(
            kind=EnvironmentKind.SETUP_PY,
            has_lock_file=False,
            material_files=["setup.py"],
        )

    # requirements.txt
    req_files = sorted(root.glob("requirements*.txt"))
    if req_files:
        return PythonEnvironment(
            kind=EnvironmentKind.REQUIREMENTS,
            has_lock_file=False,
            material_files=[f.name for f in req_files],
        )

    return PythonEnvironment(kind=EnvironmentKind.UNKNOWN)
