"""Python observability detection (stub)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ObservabilityKind(StrEnum):
    OPENTELEMETRY = "opentelemetry"
    SENTRY = "sentry"
    ABSENT = "absent"


@dataclass(frozen=True)
class ObservabilityDetection:
    kind: ObservabilityKind


def detect_observability(root: Path) -> ObservabilityDetection:
    """Detect observability tooling in *root*. Read-only."""
    return ObservabilityDetection(kind=ObservabilityKind.ABSENT)
