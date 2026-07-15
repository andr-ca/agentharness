"""Python typing tool detection.

Detects configured type checkers from project files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

try:
    import tomllib
except ImportError:  # type: ignore[import-not-found]
    import tomli as tomllib  # type: ignore[no-redef]


class TypingToolKind(StrEnum):
    MYPY = "mypy"
    PYRIGHT = "pyright"


@dataclass(frozen=True)
class TypingTool:
    kind: TypingToolKind
    config_source: str


def detect_typing_tools(root: Path) -> list[TypingTool]:
    """Return typing tools configured in *root*.  Read-only."""
    tools: list[TypingTool] = []
    pyproject = root / "pyproject.toml"

    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
        tool_section = data.get("tool", {})
        if "mypy" in tool_section:
            tools.append(TypingTool(kind=TypingToolKind.MYPY, config_source="pyproject.toml"))
        if "pyright" in tool_section:
            tools.append(TypingTool(kind=TypingToolKind.PYRIGHT, config_source="pyproject.toml"))

    for cfg_name in (".mypy.ini", "mypy.ini"):
        if (root / cfg_name).exists() and not any(t.kind == TypingToolKind.MYPY for t in tools):
            tools.append(TypingTool(kind=TypingToolKind.MYPY, config_source=cfg_name))

    if (root / "pyrightconfig.json").exists() and not any(t.kind == TypingToolKind.PYRIGHT for t in tools):
        tools.append(TypingTool(kind=TypingToolKind.PYRIGHT, config_source="pyrightconfig.json"))

    return sorted(tools, key=lambda t: t.kind)
