"""Plugin trust management.

Trust entries pin a plugin to an exact version.  Adding trust produces a
profile plan (a structured description of the required profile change) that
the operator must commit — it does not mutate any live registry directly.
This ensures every trust change goes through the same review process as
any other policy change.
"""

from __future__ import annotations

from dataclasses import dataclass


class TrustError(ValueError):
    """Raised when a trust entry is structurally invalid."""


@dataclass(frozen=True)
class TrustEntry:
    """A trust binding: a plugin pinned to an exact version.

    Only exact version strings are accepted — ranges and wildcards are
    rejected because they can be satisfied by a different artifact than
    the one the operator reviewed.
    """

    plugin_id: str
    pinned_version: str

    def __post_init__(self) -> None:
        if not self.pinned_version:
            raise TrustError(
                "pinned_version must be a non-empty exact version string"
            )
        if any(c in self.pinned_version for c in ("*", ">", "<", "^", "~")):
            raise TrustError(
                f"pinned_version must be an exact version (e.g. '1.2.3'), "
                f"not a range: {self.pinned_version!r}"
            )


class TrustRegistry:
    """Tracks trusted plugins with exact version pins.

    Mutations to the registry are only possible through commit — the
    propose_add() method returns a plan description that must be applied
    by the operator, while add() is reserved for loading committed data.
    """

    def __init__(self) -> None:
        self._trusted: dict[str, str] = {}  # plugin_id → pinned_version

    def add(self, entry: TrustEntry) -> None:
        """Add a trust entry from a committed profile (idempotent)."""
        self._trusted[entry.plugin_id] = entry.pinned_version

    def propose_add(self, entry: TrustEntry) -> str:
        """Return a plan string describing the required profile change.

        The registry is NOT updated — the caller must apply the plan to
        the committed profile and call add() after the commit is merged.
        """
        return (
            f"Trust proposal: add {entry.plugin_id!r} at version "
            f"{entry.pinned_version!r}. Commit this to "
            f".agentharness-policy/trust.yaml to activate."
        )

    def is_trusted(self, plugin_id: str, version: str) -> bool:
        """Return True if *plugin_id* at *version* is in the trust registry."""
        return self._trusted.get(plugin_id) == version
