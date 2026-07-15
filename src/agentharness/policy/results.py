"""Policy result types — EffectivePolicy, GatePlan, and GateKind."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from agentharness.policy.scope import ScopeExpression


class GateKind(StrEnum):
    """The four gate types in the bootstrap policy system."""

    COMMIT = "commit"
    PUSH = "push"
    CI = "ci"
    COMPLETION = "completion"


@dataclass(frozen=True)
class CompiledRequirement:
    """A single requirement as compiled into a gate plan."""

    requirement_id: str
    capability_id: str
    mode: str  # "strict", "warn", "grace"
    scope: ScopeExpression


@dataclass(frozen=True)
class GatePlan:
    """All requirements assigned to a specific gate."""

    gate: GateKind
    requirements: list[CompiledRequirement]


@dataclass(frozen=True)
class EffectivePolicy:
    """The compiled, immutable result of running the policy compiler.

    policy_hash: SHA-256 of the canonical JSON representation.
                 Byte-identical for identical input profiles.
    gate_plans:  One plan per gate kind, sorted by gate name.
    """

    policy_hash: str
    gate_plans: list[GatePlan]
