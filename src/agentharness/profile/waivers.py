"""Profile waivers — scoped, reasoned exemptions from policy requirements.

A waiver changes one explicit requirement's result in the evidence record.
It never mutates the compiled policy or authorizes publication.  Every
waiver must have a reason, an owner, and must reference a specific
requirement ID (no wildcards).
"""

from __future__ import annotations

from dataclasses import dataclass


class WaiverError(ValueError):
    """Raised when a waiver is structurally invalid."""


@dataclass(frozen=True)
class Waiver:
    """A scoped, reasoned exemption for a single policy requirement.

    requirement_id: the exact stable ID of the requirement being waived.
    reason:         why the waiver is needed (non-empty, no general skips).
    owner:          who is responsible for this waiver (non-empty contact).
    """

    requirement_id: str
    reason: str
    owner: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise WaiverError(
                "waiver reason must not be empty — document why the waiver is needed"
            )
        if not self.owner.strip():
            raise WaiverError(
                "waiver owner must not be empty — provide a responsible contact"
            )
        if self.requirement_id in ("*", "", "**"):
            raise WaiverError(
                "wildcard requirement IDs are not allowed in waivers — "
                "specify the exact requirement being waived"
            )


class WaiverRegistry:
    """Tracks active waivers for a profile.

    Adding a waiver records it for evidence; it does not modify the compiled
    policy.
    """

    def __init__(self) -> None:
        self._waivers: dict[str, Waiver] = {}

    def add(self, waiver: Waiver) -> None:
        """Add *waiver* to the registry (idempotent for the same ID)."""
        self._waivers[waiver.requirement_id] = waiver

    def is_waived(self, requirement_id: str) -> bool:
        """Return True if *requirement_id* has an active waiver."""
        return requirement_id in self._waivers

    def list_waivers(self) -> list[Waiver]:
        """Return all active waivers in stable order."""
        return sorted(self._waivers.values(), key=lambda w: w.requirement_id)
