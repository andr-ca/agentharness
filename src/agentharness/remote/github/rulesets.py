"""GitHub rulesets adapter — maps protection plans to ruleset API calls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RulesetConfig:
    """Minimal ruleset configuration."""

    name: str
    enforcement: str  # "active", "disabled", "evaluate"
    required_contexts: list[str]


def build_ruleset_config(name: str, required_contexts: list[str]) -> RulesetConfig:
    """Build a minimal ruleset configuration for the given contexts."""
    return RulesetConfig(
        name=name,
        enforcement="active",
        required_contexts=required_contexts,
    )
