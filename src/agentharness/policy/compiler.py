"""Policy compiler — transforms declared requirements into deterministic gate plans.

The compiler is a pure function: given the same requirements, it always
produces the same EffectivePolicy with the same hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from agentharness.policy.results import (
    CompiledRequirement,
    EffectivePolicy,
    GateKind,
    GatePlan,
)
from agentharness.policy.scope import ScopeExpression

_COMPILER_VERSION = "0.1.0"


class CompileError(ValueError):
    """Raised when the policy cannot be compiled."""


@dataclass(frozen=True)
class PolicyRequirement:
    """A single declared requirement to be compiled into a gate plan."""

    requirement_id: str
    gate: GateKind
    capability_id: str
    mode: str  # "strict", "warn", "grace"
    scope: ScopeExpression


def compile_policy(requirements: list[PolicyRequirement]) -> EffectivePolicy:
    """Compile *requirements* into a deterministic EffectivePolicy.

    Raises CompileError if:
    - requirements is empty
    - any two requirements share the same requirement_id

    Sorting is by (gate, requirement_id) — stable across process restarts.
    """
    if not requirements:
        raise CompileError("cannot compile an empty requirement list")

    seen_ids: set[str] = set()
    for req in requirements:
        if req.requirement_id in seen_ids:
            raise CompileError(
                f"duplicate requirement id: {req.requirement_id!r}"
            )
        seen_ids.add(req.requirement_id)

    # Group by gate kind
    by_gate: dict[GateKind, list[PolicyRequirement]] = {
        g: [] for g in GateKind
    }
    for req in requirements:
        by_gate[req.gate].append(req)

    # Build gate plans — only include gates that have at least one requirement
    gate_plans: list[GatePlan] = []
    for gate_kind in sorted(GateKind):
        gate_reqs = sorted(by_gate[gate_kind], key=lambda r: r.requirement_id)
        if not gate_reqs:
            continue
        compiled = [
            CompiledRequirement(
                requirement_id=r.requirement_id,
                capability_id=r.capability_id,
                mode=r.mode,
                scope=r.scope,
            )
            for r in gate_reqs
        ]
        gate_plans.append(GatePlan(gate=gate_kind, requirements=compiled))

    canonical = _canonical_json(gate_plans)
    policy_hash = hashlib.sha256(canonical.encode()).hexdigest()

    return EffectivePolicy(policy_hash=policy_hash, gate_plans=gate_plans)


def _canonical_json(gate_plans: list[GatePlan]) -> str:
    """Produce a deterministic JSON representation of the gate plans."""
    data = {
        "compiler_version": _COMPILER_VERSION,
        "gates": [
            {
                "gate": str(plan.gate),
                "requirements": [
                    {
                        "id": req.requirement_id,
                        "capability": req.capability_id,
                        "mode": req.mode,
                        "includes": [
                            p.pattern for p in req.scope.includes
                        ],
                        "excludes": [
                            p.pattern for p in req.scope.excludes
                        ],
                    }
                    for req in plan.requirements
                ],
            }
            for plan in gate_plans
        ],
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
