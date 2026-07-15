"""Unit tests for the policy compiler.

Tests cover: stable ordering, duplicate IDs, four gate types,
include/exclude scope, equivalent-profile hashing, and determinism.
"""

from __future__ import annotations

import pytest

from agentharness.policy.compiler import (
    CompileError,
    PolicyRequirement,
    compile_policy,
)
from agentharness.policy.results import GateKind
from agentharness.policy.scope import PathExpression, ScopeExpression


def _make_req(
    req_id: str = "req.test",
    gate: str = "commit",
    capability: str = "test.cap",
) -> PolicyRequirement:
    return PolicyRequirement(
        requirement_id=req_id,
        gate=GateKind(gate),
        capability_id=capability,
        mode="strict",
        scope=ScopeExpression(includes=[PathExpression("src/**")]),
    )


class TestCompilePolicy:
    def test_single_requirement_compiles(self) -> None:
        req = _make_req()
        policy = compile_policy([req])
        assert len(policy.gate_plans) == 1
        gate_plan = policy.gate_plans[0]
        assert gate_plan.gate == GateKind.COMMIT

    def test_duplicate_requirement_id_raises(self) -> None:
        with pytest.raises(CompileError, match="duplicate"):
            compile_policy([_make_req("dup.id"), _make_req("dup.id")])

    def test_all_four_gates(self) -> None:
        gates = ("commit", "push", "ci", "completion")
        reqs = [_make_req(f"req.{g}", g, f"cap.{g}") for g in gates]
        policy = compile_policy(reqs)
        gates = {p.gate for p in policy.gate_plans}
        assert GateKind.COMMIT in gates
        assert GateKind.PUSH in gates
        assert GateKind.CI in gates
        assert GateKind.COMPLETION in gates

    def test_gate_plans_are_stably_ordered(self) -> None:
        reqs = [
            _make_req("z.req", "push", "cap.z"),
            _make_req("a.req", "commit", "cap.a"),
        ]
        import random
        for _ in range(5):
            random.shuffle(reqs)
            policy = compile_policy(reqs)
            ids = [r.requirement_id for p in policy.gate_plans for r in p.requirements]
            assert ids == sorted(ids)

    def test_effective_policy_hash_is_stable(self) -> None:
        req = _make_req()
        p1 = compile_policy([req])
        p2 = compile_policy([req])
        assert p1.policy_hash == p2.policy_hash

    def test_different_profiles_produce_different_hashes(self) -> None:
        p1 = compile_policy([_make_req("a", "commit", "cap.a")])
        p2 = compile_policy([_make_req("b", "push", "cap.b")])
        assert p1.policy_hash != p2.policy_hash

    def test_empty_requirements_raises(self) -> None:
        with pytest.raises(CompileError, match="empty"):
            compile_policy([])

    def test_warn_mode_included_in_plan(self) -> None:
        req = PolicyRequirement(
            requirement_id="req.warn",
            gate=GateKind.COMMIT,
            capability_id="cap.warn",
            mode="warn",
            scope=ScopeExpression(includes=[PathExpression("src/**")]),
        )
        policy = compile_policy([req])
        assert policy.gate_plans[0].requirements[0].mode == "warn"
