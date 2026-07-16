"""Plugin runner — executes a plugin's check() method safely.

All plugin output is validated before being returned to the core.
Plugin exceptions are caught and converted to typed RunnerError values;
raw exception messages are redacted to prevent secret leakage.
"""

from __future__ import annotations

from typing import Any

from agentharness.plugins.api import CheckResult


class RunnerError(RuntimeError):
    """Raised when a plugin run fails for any reason."""


class PluginRunner:
    """Executes a plugin's check() method with output validation.

    The runner is the sole consumer of plugin return values — nothing
    else in the core calls plugin methods directly.
    """

    def run(self, plugin: Any, context: dict[str, Any]) -> CheckResult:
        """Run *plugin*.check(*context*) and return a validated CheckResult.

        Raises:
            RunnerError: if the plugin raises an exception or returns an
                         invalid result.  Raw exception text is not included
                         in the RunnerError message.
        """
        try:
            result = plugin.check(context)
        except Exception:  # noqa: BLE001
            raise RunnerError(
                f"plugin error in {plugin.metadata.plugin_id!r} — "
                "details have been redacted"
            ) from None

        if not isinstance(result, CheckResult):
            raise RunnerError(
                f"invalid result type from {plugin.metadata.plugin_id!r}: "
                f"expected CheckResult, got {type(result).__name__!r}"
            )
        return result
