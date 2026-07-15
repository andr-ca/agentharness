"""Sample quality plugin — demonstrates the plugin contract.

This sample shows every required public method with minimal, correct
behavior.  It is NOT production language support; it exists only to
demonstrate how a plugin author would structure their implementation.

Trust and version pinning
-------------------------
Before a third-party plugin can run, an operator must pin its version in
the committed profile and run `agentharness plugins trust <id> <version>`
to generate the profile plan, then commit that plan.  The bundled sample
plugin below is pre-trusted by the test harness for demonstration
purposes only.
"""

from __future__ import annotations

from agentharness.plugins.api import (
    CheckResult,
    Finding,
    FindingCode,
    PluginMetadata,
)


class SampleQualityPlugin:
    """A minimal plugin demonstrating every required public interface.

    Capabilities:
        sample.always_pass  — reports a PASS finding unconditionally.
    """

    metadata = PluginMetadata(
        plugin_id="sample.quality",
        display_name="Sample Quality Plugin",
        version="1.0.0",
        capabilities=["sample.always_pass"],
        core_version_range=">=0.1.0",
    )

    def check(self, context: object) -> CheckResult:
        """Run all checks and return a structured result.

        This implementation always returns a PASS finding for demonstration.
        A real plugin would inspect the project context and produce
        meaningful evidence.
        """
        return CheckResult(
            plugin_id=self.metadata.plugin_id,
            findings=[
                Finding(
                    capability="sample.always_pass",
                    code=FindingCode.PASS,
                    summary="Sample check passed (demonstration only).",
                    evidence={"note": "This is a sample plugin; not for production use."},
                )
            ],
        )
