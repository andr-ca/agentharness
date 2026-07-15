"""Python test framework detection.

Detects configured test frameworks from project files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

try:
    import tomllib
except ImportError:  # type: ignore[import-not-found]
    import tomli as tomllib  # type: ignore[no-redef]


class FrameworkKind(StrEnum):
    PYTEST = "pytest"
    UNITTEST = "unittest"


@dataclass(frozen=True)
class Framework:
    kind: FrameworkKind
    config_source: str


def detect_test_frameworks(root: Path) -> list[Framework]:
    """Return test frameworks configured in *root*.  Read-only."""
    frameworks: list[Framework] = []
    pyproject = root / "pyproject.toml"

    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
        tool_section = data.get("tool", {})
        if "pytest" in tool_section or "pytest.ini_options" in tool_section:
            frameworks.append(Framework(FrameworkKind.PYTEST, "pyproject.toml"))

    for cfg_name in ("pytest.ini", "setup.cfg"):
        p = root / cfg_name
        cfg = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        if "[tool:pytest]" in cfg:
            has_pytest = any(f.kind == FrameworkKind.PYTEST for f in frameworks)
            if not has_pytest:
                frameworks.append(Framework(FrameworkKind.PYTEST, cfg_name))

    return sorted(frameworks, key=lambda f: f.kind)
