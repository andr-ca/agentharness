"""Integration tests for workflow identity and gate compilation."""

from __future__ import annotations

from agentharness.policy.compiler import PolicyRequirement, compile_policy
from agentharness.policy.results import GateKind
from agentharness.policy.scope import PathExpression, ScopeExpression


class TestWorkflowIdentity:
    def test_policy_hash_is_stable_across_compilation(self) -> None:
        req = PolicyRequirement(
            requirement_id="req.ruff",
            gate=GateKind.COMMIT,
            capability_id="python.linting.ruff",
            mode="strict",
            scope=ScopeExpression(includes=[PathExpression("src/**")]),
        )
        p1 = compile_policy([req])
        p2 = compile_policy([req])
        assert p1.policy_hash == p2.policy_hash


class TestGateCompilation:
    def test_four_gates_produce_four_plans(self) -> None:
        reqs = [
            PolicyRequirement(
                requirement_id=f"req.{gate}",
                gate=GateKind(gate),
                capability_id=f"cap.{gate}",
                mode="strict",
                scope=ScopeExpression(includes=[PathExpression("src/**")]),
            )
            for gate in ("commit", "push", "ci", "completion")
        ]
        policy = compile_policy(reqs)
        assert len(policy.gate_plans) == 4

    def test_all_plans_share_same_policy_hash(self) -> None:
        reqs = [
            PolicyRequirement(
                requirement_id="req.a",
                gate=GateKind.COMMIT,
                capability_id="cap.a",
                mode="strict",
                scope=ScopeExpression(includes=[PathExpression("src/**")]),
            )
        ]
        policy = compile_policy(reqs)
        assert len(policy.policy_hash) == 64
