"""Unit tests for the bootstrap state machine.

State is a pure function of:
  - committed_profile: whether a profile is committed to source control
  - local_transaction: the local transaction record (or None)
  - ci_event: whether we're running in CI (bool)
  - proposal: the open PR state (or None)
  - default_branch_sha: the expected SHA on the default branch (or None)
  - remote_verified: whether remote configuration is verified (bool)
  - remote_complete: whether remote configuration is complete (bool)
  - drift_detected: whether drift from the last verified state was detected
"""

from __future__ import annotations

import pytest

from agentharness.bootstrap.state import (
    BootstrapState,
    LocalTransaction,
    ProposalState,
    RemoteState,
    compute_state,
)


class TestUnbootstrapped:
    def test_no_profile_no_transaction(self) -> None:
        state = compute_state(
            committed_profile=False,
            local_transaction=None,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.UNBOOTSTRAPPED

    def test_ci_without_profile_is_unbootstrapped(self) -> None:
        state = compute_state(
            committed_profile=False,
            local_transaction=None,
            ci_event=True,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.UNBOOTSTRAPPED


class TestDiscovered:
    def test_committed_profile_no_transaction(self) -> None:
        state = compute_state(
            committed_profile=True,
            local_transaction=None,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.DISCOVERED

    def test_committed_profile_ci_no_transaction(self) -> None:
        """In CI, a committed profile with no local work is still DISCOVERED."""
        state = compute_state(
            committed_profile=True,
            local_transaction=None,
            ci_event=True,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.DISCOVERED


class TestAwaitingConfirmation:
    def test_plan_generated_not_confirmed(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=False, applied=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.AWAITING_CONFIRMATION

    def test_unconfirmed_in_ci_is_awaiting(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=False, applied=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=True,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.AWAITING_CONFIRMATION


class TestLocallyApplied:
    def test_confirmed_and_applied_no_proposal(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.LOCALLY_APPLIED

    def test_confirmed_not_applied(self) -> None:
        """Confirmed but not yet applied — still waiting."""
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.AWAITING_CONFIRMATION


class TestProposalOpen:
    def test_open_pr_on_feature_branch(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=False, default_branch_sha=None)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=None,
        )
        assert state == BootstrapState.PROPOSAL_OPEN

    def test_open_pr_in_ci(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=False, default_branch_sha=None)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=True,
            proposal=proposal,
            remote=None,
        )
        assert state == BootstrapState.PROPOSAL_OPEN


class TestDefaultBranchPending:
    def test_merged_pr_awaiting_verification(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha1abc")
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=None,
        )
        assert state == BootstrapState.DEFAULT_BRANCH_PENDING


class TestRemoteIncomplete:
    def test_remote_verified_not_complete(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha1abc")
        remote = RemoteState(verified=True, complete=False, drift=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.REMOTE_INCOMPLETE


class TestActive:
    def test_fully_configured(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha1abc")
        remote = RemoteState(verified=True, complete=True, drift=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.ACTIVE

    def test_active_in_ci(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha1abc")
        remote = RemoteState(verified=True, complete=True, drift=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=True,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.ACTIVE


class TestRepairRequired:
    def test_drift_detected_on_active(self) -> None:
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha1abc")
        remote = RemoteState(verified=True, complete=True, drift=True)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.REPAIR_REQUIRED

    def test_drift_on_incomplete_remote(self) -> None:
        """Drift on an incomplete remote still requires repair."""
        txn = LocalTransaction(plan_hash="abc123", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha1abc")
        remote = RemoteState(verified=True, complete=False, drift=True)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.REPAIR_REQUIRED


class TestStateOrdering:
    """State priority: REPAIR_REQUIRED > ACTIVE > REMOTE_INCOMPLETE >
    DEFAULT_BRANCH_PENDING > PROPOSAL_OPEN > LOCALLY_APPLIED >
    AWAITING_CONFIRMATION > DISCOVERED > UNBOOTSTRAPPED.
    Drift always dominates."""

    def test_drift_dominates_active_complete(self) -> None:
        txn = LocalTransaction(plan_hash="x", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha")
        remote = RemoteState(verified=True, complete=True, drift=True)
        assert (
            compute_state(True, txn, False, proposal, remote)
            == BootstrapState.REPAIR_REQUIRED
        )

    def test_unverified_remote_dominates_not_defaulting_to_active(self) -> None:
        txn = LocalTransaction(plan_hash="x", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="sha")
        remote = RemoteState(verified=False, complete=False, drift=False)
        assert (
            compute_state(True, txn, False, proposal, remote)
            == BootstrapState.DEFAULT_BRANCH_PENDING
        )
