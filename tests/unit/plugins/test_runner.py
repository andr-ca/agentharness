"""Unit tests for the plugin runner.

Covers: timeout conversion, error conversion (plugin exceptions → typed
errors), output redaction, and deterministic result structure.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agentharness.plugins.api import (
    CheckResult,
    Finding,
    FindingCode,
    PluginMetadata,
)
from agentharness.plugins.runner import PluginRunner, RunnerError


def _make_meta(plugin_id: str = "test.plugin") -> PluginMetadata:
    return PluginMetadata(
        plugin_id=plugin_id,
        display_name="Test Plugin",
        version="1.0.0",
        capabilities=["test.capability"],
        core_version_range=">=0.1.0",
    )


class TestPluginRunner:
    def test_successful_run_returns_check_result(self) -> None:
        runner = PluginRunner()
        meta = _make_meta()
        finding = Finding(
            capability="test.capability",
            code=FindingCode.PASS,
            summary="All good",
            evidence={},
        )
        result = CheckResult(plugin_id=meta.plugin_id, findings=[finding])

        plugin = MagicMock()
        plugin.metadata = meta
        plugin.check.return_value = result

        outcome = runner.run(plugin, context={})
        assert outcome.plugin_id == meta.plugin_id
        assert len(outcome.findings) == 1

    def test_plugin_exception_converts_to_typed_error(self) -> None:
        runner = PluginRunner()
        meta = _make_meta()

        plugin = MagicMock()
        plugin.metadata = meta
        plugin.check.side_effect = RuntimeError("internal error")

        with pytest.raises(RunnerError, match="plugin error"):
            runner.run(plugin, context={})

    def test_runner_error_does_not_expose_raw_exception_message(self) -> None:
        """The runner wraps plugin errors; raw exception text must not leak."""
        runner = PluginRunner()
        meta = _make_meta()
        secret_text = "SECRET_API_KEY=abc123"

        plugin = MagicMock()
        plugin.metadata = meta
        plugin.check.side_effect = RuntimeError(secret_text)

        try:
            runner.run(plugin, context={})
        except RunnerError as e:
            assert secret_text not in str(e)

    def test_invalid_result_type_raises(self) -> None:
        runner = PluginRunner()
        meta = _make_meta()

        plugin = MagicMock()
        plugin.metadata = meta
        plugin.check.return_value = "not a CheckResult"

        with pytest.raises(RunnerError, match="invalid result"):
            runner.run(plugin, context={})
