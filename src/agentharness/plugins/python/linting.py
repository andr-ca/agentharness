"""Python linting and formatting tool detection.

Detects configured linting tools from project files. Detection is
read-only; presence is confirmed only from configuration files, not from
installed packages.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class LintToolKind(StrEnum):
    """Detected linting or formatting tool."""

    RUFF = "ruff"
    BLACK = "black"
    FLAKE8 = "flake8"
    PYLINT = "pylint"
    ISORT = "isort"


@dataclass(frozen=True)
class LintTool:
    """A detected linting or formatting tool."""

    kind: LintToolKind
    config_source: str  # "pyproject.toml", ".flake8", etc.


def detect_lint_tools(root: Path) -> list[LintTool]:
    """Return linting tools configured in *root*.

    Detection is read-only and has no side effects.
    """
    tools: list[LintTool] = []
    pyproject = root / "pyproject.toml"

    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
        tool_section = data.get("tool", {})
        if "ruff" in tool_section:
            tools.append(LintTool(LintToolKind.RUFF, "pyproject.toml"))
        if "black" in tool_section:
            tools.append(LintTool(LintToolKind.BLACK, "pyproject.toml"))
        if "pylint" in tool_section:
            tools.append(LintTool(LintToolKind.PYLINT, "pyproject.toml"))
        if "isort" in tool_section:
            tools.append(LintTool(LintToolKind.ISORT, "pyproject.toml"))

    # Stand-alone config files
    for filename, kind in (
        (".flake8", LintToolKind.FLAKE8),
        ("setup.cfg", LintToolKind.FLAKE8),
    ):
        candidate = root / filename
        if not candidate.exists():
            continue
        cfg_text = candidate.read_text(encoding="utf-8", errors="replace")
        if "[flake8]" in cfg_text:
            if not any(t.kind == LintToolKind.FLAKE8 for t in tools):
                tools.append(LintTool(LintToolKind.FLAKE8, filename))

    if (root / ".isort.cfg").exists():
        if not any(t.kind == LintToolKind.ISORT for t in tools):
            tools.append(LintTool(LintToolKind.ISORT, ".isort.cfg"))

    return sorted(tools, key=lambda t: t.kind)
