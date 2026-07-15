"""Shared compliance assertions for bootstrap plugins.

Every plugin implementation (bundled or third-party) must pass these
assertions.  Use assert_plugin_compliant() in contract tests.
"""

from __future__ import annotations

from typing import Any

from agentharness.plugins.api import CheckResult, FindingCode, PluginMetadata
from agentharness.plugins.runner import PluginRunner, RunnerError


class ComplianceError(AssertionError):
    """Raised when a plugin fails a contract assertion."""


def assert_plugin_compliant(plugin: Any, context: dict[str, Any] | None = None) -> CheckResult:
    """Assert *plugin* meets the full plugin contract.

    Raises ComplianceError with a descriptive message on any violation.
    Returns the CheckResult for further inspection.
    """
    ctx = context or {}

    # 1. Metadata must be present and valid
    meta = _assert_has_metadata(plugin)

    # 2. Run must return a CheckResult
    runner = PluginRunner()
    try:
        result = runner.run(plugin, ctx)
    except RunnerError as e:
        raise ComplianceError(f"Plugin check() raised a RunnerError: {e}") from e

    # 3. Result must match declared plugin_id
    if result.plugin_id != meta.plugin_id:
        raise ComplianceError(
            f"result.plugin_id {result.plugin_id!r} != "
            f"meta.plugin_id {meta.plugin_id!r}"
        )

    # 4. Every finding must reference a declared capability
    declared = set(meta.capabilities)
    for finding in result.findings:
        if finding.capability not in declared:
            raise ComplianceError(
                f"Finding references undeclared capability {finding.capability!r}. "
                f"Declared: {sorted(declared)}"
            )
        if finding.code not in FindingCode.__members__.values():
            raise ComplianceError(
                f"Finding has invalid code {finding.code!r}"
            )
        if not finding.summary.strip():
            raise ComplianceError(
                f"Finding for {finding.capability!r} has empty summary"
            )

    return result


def _assert_has_metadata(plugin: Any) -> PluginMetadata:
    if not hasattr(plugin, "metadata"):
        raise ComplianceError(
            f"{type(plugin).__name__} has no 'metadata' attribute"
        )
    meta = plugin.metadata
    if not isinstance(meta, PluginMetadata):
        raise ComplianceError(
            f"plugin.metadata must be a PluginMetadata instance, "
            f"got {type(meta).__name__!r}"
        )
    return meta
