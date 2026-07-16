"""Python configuration management detection (stub)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ConfigKind(StrEnum):
    ENV_SAMPLE = "env_sample"
    ABSENT = "absent"


@dataclass(frozen=True)
class ConfigDetection:
    kind: ConfigKind


def detect_configuration(root: Path) -> ConfigDetection:
    """Detect configuration management in *root*. Read-only."""
    if (root / ".env.sample").exists() or (root / ".env.example").exists():
        return ConfigDetection(kind=ConfigKind.ENV_SAMPLE)
    return ConfigDetection(kind=ConfigKind.ABSENT)
