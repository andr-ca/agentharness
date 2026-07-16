from __future__ import annotations

from dataclasses import dataclass

from agentharness.profile.schema import (
    BootstrapMode,
    LocalOverride,
    PerformanceOverride,
    PresentationOverride,
    Profile,
    ProfileError,
    Requirement,
)


@dataclass(frozen=True, slots=True)
class Reduction:
    code: str
    subject: str


@dataclass(frozen=True, slots=True)
class EffectiveProfile:
    profile: Profile
    presentation: PresentationOverride
    performance: PerformanceOverride


_MODE_STRENGTH = {
    BootstrapMode.WARN: 0,
    BootstrapMode.GRACE: 1,
    BootstrapMode.STRICT: 2,
}
_RIGOR_STRENGTH = {"prototype": 0, "internal": 1, "production": 2}
_PUBLICATION_STRENGTH = {
    "local_only": 0,
    "follow_publish_authority": 1,
    "required": 2,
}


def _requirement_reductions(
    base: Requirement, candidate: Requirement
) -> list[Reduction]:
    findings: list[Reduction] = []
    subject = f"requirements.{base.identifier}"
    if base.enabled and not candidate.enabled:
        findings.append(Reduction("reduction.requirement_disabled", subject))
    if base.provider != candidate.provider:
        findings.append(Reduction("reduction.provider_changed", subject))
    if (base.tool, base.command, base.standard, base.checks) != (
        candidate.tool,
        candidate.command,
        candidate.standard,
        candidate.checks,
    ):
        findings.append(Reduction("reduction.verifier_changed", subject))
    for field in ("minimum_coverage", "minimum_score"):
        old = getattr(base, field)
        new = getattr(candidate, field)
        if old is not None and (new is None or new < old):
            findings.append(
                Reduction("reduction.threshold_decreased", f"{subject}.{field}")
            )
    if not set(base.gates).issubset(candidate.gates):
        findings.append(Reduction("reduction.gate_removed", subject))
    base_includes = set(base.scope.include)
    candidate_includes = set(candidate.scope.include)
    include_narrowed = (not base_includes and bool(candidate_includes)) or (
        bool(base_includes)
        and bool(candidate_includes)
        and not base_includes.issubset(candidate_includes)
    )
    if include_narrowed or not set(candidate.scope.exclude).issubset(
        base.scope.exclude
    ):
        findings.append(Reduction("reduction.scope_narrowed", subject))
    if not set(base.required_for).issubset(candidate.required_for):
        findings.append(Reduction("reduction.scope_narrowed", subject))
    return findings


def find_reductions(base: Profile, candidate: Profile) -> tuple[Reduction, ...]:
    findings: list[Reduction] = []
    if base.runtime != candidate.runtime:
        findings.append(Reduction("reduction.runtime_changed", "runtime"))
    if _RIGOR_STRENGTH[candidate.project.rigor] < _RIGOR_STRENGTH[base.project.rigor]:
        findings.append(Reduction("reduction.rigor_weakened", "project.rigor"))
    if _MODE_STRENGTH[candidate.bootstrap.mode] < _MODE_STRENGTH[base.bootstrap.mode]:
        findings.append(
            Reduction("reduction.bootstrap_mode_weakened", "bootstrap.mode")
        )
    if (
        base.bootstrap.existing_checks_are_required
        and not candidate.bootstrap.existing_checks_are_required
    ):
        findings.append(
            Reduction(
                "reduction.bootstrap_weakened",
                "bootstrap.existing_checks_are_required",
            )
        )

    base_plugins = {item.identifier: item for item in base.plugins}
    candidate_plugins = {item.identifier: item for item in candidate.plugins}
    for identifier, plugin in base_plugins.items():
        changed_plugin = candidate_plugins.get(identifier)
        subject = f"plugins.{identifier}"
        if changed_plugin is None:
            findings.append(Reduction("reduction.plugin_removed", subject))
        elif plugin.enabled and not changed_plugin.enabled:
            findings.append(Reduction("reduction.plugin_disabled", subject))
        if changed_plugin is not None and (
            plugin.version != changed_plugin.version
            or plugin.config != changed_plugin.config
        ):
            findings.append(Reduction("reduction.plugin_identity_changed", subject))
    base_requirements = {item.identifier: item for item in base.requirements}
    candidate_requirements = {item.identifier: item for item in candidate.requirements}
    for identifier, requirement in base_requirements.items():
        changed = candidate_requirements.get(identifier)
        if changed is None:
            findings.append(
                Reduction("reduction.requirement_removed", f"requirements.{identifier}")
            )
        else:
            findings.extend(_requirement_reductions(requirement, changed))

    base_signals = {
        (signal.type, signal.name): signal
        for signal in base.workflow.reviews.expected_signals
    }
    candidate_signals = {
        (signal.type, signal.name): signal
        for signal in candidate.workflow.reviews.expected_signals
    }
    for identity, signal in base_signals.items():
        changed_signal = candidate_signals.get(identity)
        subject = f"workflow.reviews.expected_signals.{identity[0]}.{identity[1]}"
        if changed_signal is None:
            findings.append(Reduction("reduction.review_signal_removed", subject))
        elif changed_signal != signal:
            findings.append(Reduction("reduction.review_signal_changed", subject))
    if (
        candidate.workflow.reviews.stabilization_seconds
        < base.workflow.reviews.stabilization_seconds
    ):
        findings.append(
            Reduction(
                "reduction.review_window_weakened",
                "workflow.reviews.stabilization_seconds",
            )
        )
    if (
        candidate.workflow.reviews.timeout_seconds
        != base.workflow.reviews.timeout_seconds
    ):
        findings.append(
            Reduction(
                "reduction.review_window_changed",
                "workflow.reviews.timeout_seconds",
            )
        )
    if (
        base.workflow.completion.require_clean_tree
        and not candidate.workflow.completion.require_clean_tree
    ):
        findings.append(
            Reduction(
                "reduction.completion_weakened",
                "workflow.completion.require_clean_tree",
            )
        )
    if (
        base.workflow.completion.require_current_ci
        and not candidate.workflow.completion.require_current_ci
    ):
        findings.append(
            Reduction(
                "reduction.completion_weakened",
                "workflow.completion.require_current_ci",
            )
        )
    if (
        base.workflow.completion.require_committed_changes
        and not candidate.workflow.completion.require_committed_changes
    ):
        findings.append(
            Reduction(
                "reduction.completion_weakened",
                "workflow.completion.require_committed_changes",
            )
        )
    if (
        base.workflow.completion.require_resolved_reviews
        and not candidate.workflow.completion.require_resolved_reviews
    ):
        findings.append(
            Reduction(
                "reduction.completion_weakened",
                "workflow.completion.require_resolved_reviews",
            )
        )
    if (
        _PUBLICATION_STRENGTH[candidate.workflow.completion.publication]
        < _PUBLICATION_STRENGTH[base.workflow.completion.publication]
    ):
        findings.append(
            Reduction(
                "reduction.completion_weakened",
                "workflow.completion.publication",
            )
        )
    if (
        base.protection.provider != candidate.protection.provider
        or base.protection.default_branch != candidate.protection.default_branch
    ):
        findings.append(
            Reduction(
                "reduction.protection_identity_changed",
                "protection",
            )
        )
    base_reductions = base.protection.requirement_reductions
    candidate_reductions = candidate.protection.requirement_reductions
    if (
        base_reductions.require_codeowner_approval
        and not candidate_reductions.require_codeowner_approval
    ):
        findings.append(
            Reduction(
                "reduction.protection_weakened",
                "protection.requirement_reductions.require_codeowner_approval",
            )
        )
    if set(base_reductions.codeowners) != set(candidate_reductions.codeowners):
        findings.append(
            Reduction(
                "reduction.protection_codeowners_changed",
                "protection.requirement_reductions.codeowners",
            )
        )
    if (
        base_reductions.minimum_total_approvals
        > candidate_reductions.minimum_total_approvals
    ):
        findings.append(
            Reduction(
                "reduction.protection_weakened",
                "protection.requirement_reductions.minimum_total_approvals",
            )
        )
    if (
        base.protection.waivers.require_expiry
        and not candidate.protection.waivers.require_expiry
    ):
        findings.append(
            Reduction("reduction.waiver_weakened", "protection.waivers.require_expiry")
        )
    if (
        base.protection.waivers.require_reason
        and not candidate.protection.waivers.require_reason
    ):
        findings.append(
            Reduction("reduction.waiver_weakened", "protection.waivers.require_reason")
        )
    return tuple(findings)


def apply_local_override(
    profile: Profile,
    override: LocalOverride,
    *,
    verifier_max_timeout_seconds: int,
) -> EffectiveProfile:
    timeout = override.performance.timeout_seconds
    if timeout is not None and timeout > verifier_max_timeout_seconds:
        raise ProfileError(
            "override.timeout_exceeds_bound",
            "local timeout exceeds the verifier's trusted bound",
        )
    return EffectiveProfile(profile, override.presentation, override.performance)
