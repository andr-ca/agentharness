"""Contract tests for bundled plugins.

Each broken fixture must fail with ComplianceError; no real plugin
should fail any compliance assertion.
"""

from __future__ import annotations

import pytest

from tests.contract.conftest import (
    EmptySummaryPlugin,
    ExceptionPlugin,
    InvalidResultPlugin,
    NoMetadataPlugin,
    UndeclaredCapabilityPlugin,
    WrongPluginIdPlugin,
)
from tests.contract.plugin_compliance import ComplianceError, assert_plugin_compliant


class TestBrokenFixturesMustFail:
    """Each broken fixture must raise ComplianceError for the right reason."""

    def test_no_metadata_fails(self) -> None:
        with pytest.raises(ComplianceError, match="metadata"):
            assert_plugin_compliant(NoMetadataPlugin())

    def test_wrong_plugin_id_fails(self) -> None:
        with pytest.raises(ComplianceError, match="plugin_id"):
            assert_plugin_compliant(WrongPluginIdPlugin())

    def test_undeclared_capability_fails(self) -> None:
        with pytest.raises(ComplianceError, match="undeclared"):
            assert_plugin_compliant(UndeclaredCapabilityPlugin())

    def test_empty_summary_fails(self) -> None:
        with pytest.raises(ComplianceError, match="empty summary"):
            assert_plugin_compliant(EmptySummaryPlugin())

    def test_exception_in_check_fails(self) -> None:
        with pytest.raises(ComplianceError, match="RunnerError"):
            assert_plugin_compliant(ExceptionPlugin())

    def test_invalid_result_fails(self) -> None:
        with pytest.raises(ComplianceError, match="RunnerError"):
            assert_plugin_compliant(InvalidResultPlugin())

    def test_exception_does_not_leak_secrets(self) -> None:
        """Secret text in a plugin exception must not appear in ComplianceError."""
        try:
            assert_plugin_compliant(ExceptionPlugin())
        except ComplianceError as e:
            assert "SECRET_TOKEN" not in str(e)
