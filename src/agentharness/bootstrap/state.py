"""Bootstrap state machine.

State is a pure function of committed profile, local transaction record,
CI context, open proposal, and remote configuration state.  No side
effects occur here; callers are responsible for reading the inputs and
acting on the returned state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BootstrapState(StrEnum):
    """The ordered states of the bootstrap process.

    Priority (highest → lowest) when multiple conditions apply:
    REPAIR_REQUIRED > ACTIVE > REMOTE_INCOMPLETE > DEFAULT_BRANCH_PENDING
    > PROPOSAL_OPEN > LOCALLY_APPLIED > AWAITING_CONFIRMATION
    > DISCOVERED > UNBOOTSTRAPPED
    """

    REPAIR_REQUIRED = "repair-required"
    ACTIVE = "active"
    REMOTE_INCOMPLETE = "remote-incomplete"
    DEFAULT_BRANCH_PENDING = "default-branch-pending"
    PROPOSAL_OPEN = "proposal-open"
    LOCALLY_APPLIED = "locally-applied"
    AWAITING_CONFIRMATION = "awaiting-confirmation"
    DISCOVERED = "discovered"
    UNBOOTSTRAPPED = "unbootstrapped"


@dataclass(frozen=True)
class LocalTransaction:
    """The persisted local transaction record.

    plan_hash: SHA-256 hex digest of the canonical plan that was shown to
               the operator for confirmation.
    confirmed: True once the operator has accepted the plan.
    applied:   True once all local filesystem changes have been committed.
    """

    plan_hash: str
    confirmed: bool
    applied: bool


@dataclass(frozen=True)
class ProposalState:
    """The state of an open (or recently merged) pull request.

    merged:              True once the PR has been merged.
    default_branch_sha:  The expected commit SHA on the default branch after
                         the merge (None until the merge is confirmed).
    """

    merged: bool
    default_branch_sha: str | None


@dataclass(frozen=True)
class RemoteState:
    """The state of remote configuration verification.

    verified: True once the default-branch SHA has been confirmed present.
    complete: True once all required remote configuration (e.g. branch
              protection) has been verified as active.
    drift:    True if any previously verified setting has changed since the
              last successful verification.
    """

    verified: bool
    complete: bool
    drift: bool


def compute_state(
    committed_profile: bool,
    local_transaction: LocalTransaction | None,
    ci_event: bool,  # noqa: ARG001 — reserved for future CI-specific transitions
    proposal: ProposalState | None,
    remote: RemoteState | None,
) -> BootstrapState:
    """Return the current bootstrap state as a pure function of its inputs.

    Evaluate conditions from highest priority to lowest and return the first
    match.  Callers must not mutate state; call this function again after
    any update to the inputs.
    """
    # --- Drift always dominates -----------------------------------------------
    if remote is not None and remote.drift:
        return BootstrapState.REPAIR_REQUIRED

    # --- Remote configuration verified and complete ----------------------------
    if remote is not None and remote.verified and remote.complete:
        return BootstrapState.ACTIVE

    # --- Remote configuration verified but not complete ------------------------
    if remote is not None and remote.verified and not remote.complete:
        return BootstrapState.REMOTE_INCOMPLETE

    # --- PR merged; waiting for default-branch verification -------------------
    if proposal is not None and proposal.merged:
        return BootstrapState.DEFAULT_BRANCH_PENDING

    # --- PR open on a feature branch ------------------------------------------
    if proposal is not None and not proposal.merged:
        return BootstrapState.PROPOSAL_OPEN

    # --- No proposal yet; check local transaction state -----------------------
    if local_transaction is not None:
        if local_transaction.confirmed and local_transaction.applied:
            return BootstrapState.LOCALLY_APPLIED
        # Confirmed-but-not-applied or unconfirmed
        return BootstrapState.AWAITING_CONFIRMATION

    # --- Profile committed; no local work started yet -------------------------
    if committed_profile:
        return BootstrapState.DISCOVERED

    # --- Nothing at all -------------------------------------------------------
    return BootstrapState.UNBOOTSTRAPPED
