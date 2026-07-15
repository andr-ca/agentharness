"""Legacy profile migration — import .agentharness-profile data.

Reads the legacy single-line tier selector, maps it to a structured
profile record with provenance, and classifies unknown tiers as
``legacy-deferred`` rather than failing hard.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

_KNOWN_TIERS = frozenset({"prototype", "internal", "production"})


class MigrationConflictError(ValueError):
    """Raised when legacy profile data is structurally invalid."""


@dataclass(frozen=True)
class LegacyProfile:
    """The result of parsing a legacy .agentharness-profile file.

    tier:         the canonical tier name, or ``"legacy-deferred"`` for
                  unknown selectors.
    raw_selector: the original string read from the file (before mapping).
    """

    tier: str
    raw_selector: str

    @classmethod
    def parse(cls, selector: str) -> "LegacyProfile":
        """Parse a raw selector string from a legacy profile file.

        Raises MigrationConflictError for empty or whitespace-only selectors.
        Unknown selectors are classified as ``legacy-deferred`` rather than
        raising — the caller decides whether to block on that state.
        """
        stripped = selector.strip()
        if not stripped:
            raise MigrationConflictError(
                "Legacy profile selector must not be empty or whitespace-only"
            )
        if stripped in _KNOWN_TIERS:
            return cls(tier=stripped, raw_selector=stripped)
        return cls(tier="legacy-deferred", raw_selector=stripped)


def read_legacy_profile_file(path: Path) -> str:
    """Read and return the tier selector from a legacy profile file.

    Raises:
        FileNotFoundError:    if the file does not exist.
        MigrationConflictError: if the file is empty or whitespace-only.
    """
    if not path.exists():
        raise FileNotFoundError(f"Legacy profile not found: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise MigrationConflictError(
            f"Legacy profile file {path} is empty — cannot import"
        )
    return content


def import_legacy_profile(selector: str) -> dict[str, Any]:
    """Import a legacy selector into a structured profile record.

    Returns a dict with keys:
      tier:       the canonical tier (or "legacy-deferred")
      provenance: metadata about the import source

    The returned dict is safe to serialise as JSON.
    """
    profile = LegacyProfile.parse(selector)
    provenance: dict[str, str] = {
        "source": "legacy-.agentharness-profile",
        "legacy_selector": profile.raw_selector,
    }
    return {
        "tier": profile.tier,
        "provenance": provenance,
    }
