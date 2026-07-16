"""Broken plugin fixtures for contract compliance meta-tests.

Each fixture intentionally violates one contract rule.  Contract tests
verify that assert_plugin_compliant() raises ComplianceError for each.
"""

from __future__ import annotations

from agentharness.plugins.api import CheckResult, Finding, FindingCode, PluginMetadata


class _GoodMeta:
    """Shared valid metadata used by the broken fixtures below."""

    metadata = PluginMetadata(
        plugin_id="fixture.broken",
        display_name="Broken Fixture",
        version="1.0.0",
        capabilities=["fixture.capability"],
        core_version_range=">=0.1.0",
    )


class NoMetadataPlugin:
    """Fixture: plugin has no .metadata attribute."""

    def check(self, context: object) -> CheckResult:
        return CheckResult(plugin_id="", findings=[])


class WrongPluginIdPlugin(_GoodMeta):
    """Fixture: result.plugin_id does not match metadata.plugin_id."""

    def check(self, context: object) -> CheckResult:
        return CheckResult(
            plugin_id="wrong.plugin.id",
            findings=[
                Finding(
                    capability="fixture.capability",
                    code=FindingCode.PASS,
                    summary="OK",
                )
            ],
        )


class UndeclaredCapabilityPlugin(_GoodMeta):
    """Fixture: finding references a capability not in metadata.capabilities."""

    def check(self, context: object) -> CheckResult:
        return CheckResult(
            plugin_id="fixture.broken",
            findings=[
                Finding(
                    capability="undeclared.capability",
                    code=FindingCode.PASS,
                    summary="OK",
                )
            ],
        )


class EmptySummaryPlugin(_GoodMeta):
    """Fixture: finding has an empty summary string."""

    def check(self, context: object) -> CheckResult:
        return CheckResult(
            plugin_id="fixture.broken",
            findings=[
                Finding(
                    capability="fixture.capability",
                    code=FindingCode.PASS,
                    summary="   ",  # whitespace-only
                )
            ],
        )


class ExceptionPlugin(_GoodMeta):
    """Fixture: plugin raises an exception from check()."""

    def check(self, context: object) -> CheckResult:
        raise RuntimeError("internal plugin error with SECRET_TOKEN=abc123")


class InvalidResultPlugin(_GoodMeta):
    """Fixture: plugin returns a non-CheckResult value."""

    def check(self, context: object) -> str:  # type: ignore[override]
        return "not a CheckResult"
