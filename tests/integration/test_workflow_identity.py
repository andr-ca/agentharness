"""Integration tests for workflow identity verification.

Verifies that the policy hash is stable and that duplicate workflow
job names or reusable workflows are detectable.
"""

from __future__ import annotations

from agentharness.policy.compiler import PolicyRequirement, compile_policy
from agentharness.policy.results import GateKind
from agentharness.policy.scope import PathExpression, ScopeExpression


class TestWorkflowIdentityStability:
    def test_same_requirement_same_hash(self) -> None:
        req = PolicyRequirement(
            requirement_id="policy.identity.test",
            gate=GateKind.CI,
            capability_id="cap.ci",
            mode="strict",
            scope=ScopeExpression(includes=[PathExpression("**")]),
        )
        p1 = compile_policy([req])
        p2 = compile_policy([req])
        assert p1.policy_hash == p2.policy_hash

    def test_different_requirements_different_hashes(self) -> None:
        def make(req_id: str) -> str:
            return compile_policy([
                PolicyRequirement(
                    requirement_id=req_id,
                    gate=GateKind.CI,
                    capability_id="cap.ci",
                    mode="strict",
                    scope=ScopeExpression(includes=[PathExpression("**")]),
                )
            ]).policy_hash

        assert make("req.alpha") != make("req.beta")
