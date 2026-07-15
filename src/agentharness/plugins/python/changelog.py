"""Python changelog tooling detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ChangelogKind(StrEnum):
    TOWNCRIER = "towncrier"
    KEEPACHANGELOG = "keepachangelog"
    ABSENT = "absent"


@dataclass(frozen=True)
class ChangelogDetection:
    kind: ChangelogKind


def detect_changelog(root: Path) -> ChangelogDetection:
    """Detect changelog tooling in *root*. Read-only."""
    if (root / "changelog.d").exists() or (root / "newsfragments").exists():
        return ChangelogDetection(kind=ChangelogKind.TOWNCRIER)
    changelog = root / "CHANGELOG.md"
    if changelog.exists() and "Keep a Changelog" in changelog.read_text(
        encoding="utf-8", errors="replace"
    ):
        return ChangelogDetection(kind=ChangelogKind.KEEPACHANGELOG)
    return ChangelogDetection(kind=ChangelogKind.ABSENT)
