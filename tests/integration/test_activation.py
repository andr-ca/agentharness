"""Integration tests for bootstrap activation state transitions.

Covers the post-local-application flow: PR open → merged → verified →
active, and the repair path when drift is detected.
"""

from __future__ import annotations

from agentharness.bootstrap.state import (
    BootstrapState,
    LocalTransaction,
    ProposalState,
    RemoteState,
    compute_state,
)

_BASE_TXN = LocalTransaction(plan_hash="hash1", confirmed=True, applied=True)


class TestActivationFlow:
    def test_pr_open_is_proposal_open(self) -> None:
        proposal = ProposalState(merged=False, default_branch_sha=None)
        state = compute_state(
            committed_profile=True,
            local_transaction=_BASE_TXN,
            ci_event=False,
            proposal=proposal,
            remote=None,
        )
        assert state == BootstrapState.PROPOSAL_OPEN

    def test_pr_merged_is_default_branch_pending(self) -> None:
        proposal = ProposalState(merged=True, default_branch_sha="sha1")
        state = compute_state(
            committed_profile=True,
            local_transaction=_BASE_TXN,
            ci_event=False,
            proposal=proposal,
            remote=None,
        )
        assert state == BootstrapState.DEFAULT_BRANCH_PENDING

    def test_remote_verified_incomplete_is_remote_incomplete(self) -> None:
        proposal = ProposalState(merged=True, default_branch_sha="sha1")
        remote = RemoteState(verified=True, complete=False, drift=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=_BASE_TXN,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.REMOTE_INCOMPLETE

    def test_remote_complete_is_active(self) -> None:
        proposal = ProposalState(merged=True, default_branch_sha="sha1")
        remote = RemoteState(verified=True, complete=True, drift=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=_BASE_TXN,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.ACTIVE

    def test_drift_detected_requires_repair(self) -> None:
        proposal = ProposalState(merged=True, default_branch_sha="sha1")
        remote = RemoteState(verified=True, complete=True, drift=True)
        state = compute_state(
            committed_profile=True,
            local_transaction=_BASE_TXN,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.REPAIR_REQUIRED

    def test_initial_proposal_mode_ci(self) -> None:
        """CI running against a feature branch with an open PR."""
        proposal = ProposalState(merged=False, default_branch_sha=None)
        state = compute_state(
            committed_profile=True,
            local_transaction=_BASE_TXN,
            ci_event=True,
            proposal=proposal,
            remote=None,
        )
        assert state == BootstrapState.PROPOSAL_OPEN
