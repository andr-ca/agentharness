"""Python task runner detection.

Detects tox, nox, and Makefile-based task runners in a Python project.
Detection is read-only and never executes any command.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class TaskRunnerKind(StrEnum):
    """The type of task runner detected."""

    TOX = "tox"
    NOX = "nox"
    MAKE = "make"
    HATCH = "hatch"
    INVOKE = "invoke"


@dataclass(frozen=True)
class TaskRunner:
    """A detected task runner in a Python project."""

    kind: TaskRunnerKind
    config_file: str
    declared_targets: list[str] = field(default_factory=list)


def detect_task_runners(root: Path) -> list[TaskRunner]:
    """Return all task runners detected in *root*.

    Scans for known configuration files (tox.ini, noxfile.py, Makefile,
    etc.).  Returns an empty list if no runners are found.

    This function is pure and read-only — it never writes any file.
    """
    runners: list[TaskRunner] = []

    if (root / "tox.ini").exists():
        runners.append(TaskRunner(kind=TaskRunnerKind.TOX, config_file="tox.ini"))

    if (root / "noxfile.py").exists():
        runners.append(TaskRunner(kind=TaskRunnerKind.NOX, config_file="noxfile.py"))

    makefile = root / "Makefile"
    if makefile.exists():
        targets = _extract_makefile_phony_targets(makefile)
        runners.append(
            TaskRunner(
                kind=TaskRunnerKind.MAKE,
                config_file="Makefile",
                declared_targets=sorted(targets),
            )
        )

    if (root / "hatch.toml").exists():
        runners.append(TaskRunner(kind=TaskRunnerKind.HATCH, config_file="hatch.toml"))

    if (root / "tasks.py").exists():
        runners.append(TaskRunner(kind=TaskRunnerKind.INVOKE, config_file="tasks.py"))

    # Sort by TaskRunnerKind for determinism
    return sorted(runners, key=lambda r: r.kind)


_PHONY_RE = re.compile(r"^\.PHONY\s*:\s*(.+)$", re.MULTILINE)


def _extract_makefile_phony_targets(path: Path) -> list[str]:
    """Return all .PHONY targets declared in *path*."""
    content = path.read_text(encoding="utf-8", errors="replace")
    targets: list[str] = []
    for match in _PHONY_RE.finditer(content):
        targets.extend(t.strip() for t in match.group(1).split())
    return targets
