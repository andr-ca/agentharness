"""Contract tests for the sample quality plugin.

These tests use the shared compliance assertions from tests/contract/
and must pass without importing any private test helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the examples directory importable from this standalone test file
sys.path.insert(0, str(Path(__file__).parent))

from plugin import SampleQualityPlugin

# Reach the compliance suite through the installed package path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tests"))

from contract.plugin_compliance import assert_plugin_compliant
from agentharness.plugins.api import FindingCode


class TestSamplePluginContractCompliance:
    def test_metadata_is_valid(self) -> None:
        plugin = SampleQualityPlugin()
        meta = plugin.metadata
        assert meta.plugin_id == "sample.quality"
        assert "sample.always_pass" in meta.capabilities

    def test_passes_full_compliance_suite(self) -> None:
        plugin = SampleQualityPlugin()
        result = assert_plugin_compliant(plugin)
        assert result.plugin_id == "sample.quality"

    def test_check_returns_pass_finding(self) -> None:
        plugin = SampleQualityPlugin()
        result = plugin.check({})
        assert len(result.findings) == 1
        assert result.findings[0].code == FindingCode.PASS

    def test_finding_has_nonempty_summary(self) -> None:
        plugin = SampleQualityPlugin()
        result = plugin.check({})
        assert result.findings[0].summary.strip()
