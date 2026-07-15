"""Python logging library detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

try:
    import tomllib
except ImportError:  # type: ignore[import-not-found]
    import tomli as tomllib  # type: ignore[no-redef]


class LoggingKind(StrEnum):
    STDLIB = "stdlib"
    STRUCTLOG = "structlog"
    LOGURU = "loguru"
    ABSENT = "absent"


@dataclass(frozen=True)
class LoggingDetection:
    kind: LoggingKind
    confidence: str  # "detected", "configured", "enforced"


def detect_logging(root: Path) -> LoggingDetection:
    """Detect the logging library used in *root*. Read-only."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return LoggingDetection(kind=LoggingKind.ABSENT, confidence="detected")

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return LoggingDetection(kind=LoggingKind.ABSENT, confidence="detected")

    deps: list[str] = []
    deps.extend(data.get("project", {}).get("dependencies", []))
    for extra in data.get("project", {}).get("optional-dependencies", {}).values():
        deps.extend(extra)

    dep_lower = " ".join(deps).lower()
    if "structlog" in dep_lower:
        return LoggingDetection(kind=LoggingKind.STRUCTLOG, confidence="detected")
    if "loguru" in dep_lower:
        return LoggingDetection(kind=LoggingKind.LOGURU, confidence="detected")
    return LoggingDetection(kind=LoggingKind.STDLIB, confidence="detected")
