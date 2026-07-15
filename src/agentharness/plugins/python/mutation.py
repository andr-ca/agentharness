"""Python mutation testing detection."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class MutationKind(StrEnum):
    MUTMUT = "mutmut"
    COSMIC_RAY = "cosmic_ray"
    ABSENT = "absent"


@dataclass(frozen=True)
class MutationDetection:
    kind: MutationKind


def detect_mutation(root: Path) -> MutationDetection:
    """Detect mutation testing tooling in *root*. Read-only."""
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
        if "mutmut" in data.get("tool", {}):
            return MutationDetection(kind=MutationKind.MUTMUT)

    if (root / "cosmic-ray.toml").exists() or (root / ".cosmic-ray.cfg").exists():
        return MutationDetection(kind=MutationKind.COSMIC_RAY)

    return MutationDetection(kind=MutationKind.ABSENT)
