"""Integration tests for first-use bootstrap flow.

These tests verify the end-to-end state transitions when an operator
runs `agentharness bootstrap` for the first time in a project.
"""

from __future__ import annotations

from agentharness.bootstrap.state import (
    BootstrapState,
    LocalTransaction,
    ProposalState,
    RemoteState,
    compute_state,
)


class TestFirstUseFlow:
    """Simulate the complete first-use state progression."""

    def test_initial_state_is_unbootstrapped(self) -> None:
        state = compute_state(
            committed_profile=False,
            local_transaction=None,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.UNBOOTSTRAPPED

    def test_after_profile_commit_is_discovered(self) -> None:
        state = compute_state(
            committed_profile=True,
            local_transaction=None,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.DISCOVERED

    def test_plan_generated_awaiting_confirmation(self) -> None:
        txn = LocalTransaction(plan_hash="hash1", confirmed=False, applied=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.AWAITING_CONFIRMATION

    def test_confirmed_and_applied_is_locally_applied(self) -> None:
        txn = LocalTransaction(plan_hash="hash1", confirmed=True, applied=True)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=None,
            remote=None,
        )
        assert state == BootstrapState.LOCALLY_APPLIED

    def test_full_flow_reaches_active(self) -> None:
        txn = LocalTransaction(plan_hash="hash1", confirmed=True, applied=True)
        proposal = ProposalState(merged=True, default_branch_sha="abc123")
        remote = RemoteState(verified=True, complete=True, drift=False)
        state = compute_state(
            committed_profile=True,
            local_transaction=txn,
            ci_event=False,
            proposal=proposal,
            remote=remote,
        )
        assert state == BootstrapState.ACTIVE
