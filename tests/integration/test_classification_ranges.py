"""Integration tests for classification ranges."""

from __future__ import annotations

from agentharness.policy.classification import ChangeClass, classify_path


class TestClassificationRanges:
    def test_commit_python_change_classified_as_code(self) -> None:
        assert classify_path("src/cli.py") == ChangeClass.CODE

    def test_push_test_change_classified_as_tests(self) -> None:
        assert classify_path("tests/integration/test_api.py") == ChangeClass.TESTS

    def test_pr_docs_change_classified_correctly(self) -> None:
        assert classify_path("docs/ARCHITECTURE.md") == ChangeClass.DOCS

    def test_config_change_classified(self) -> None:
        assert classify_path("pyproject.toml") == ChangeClass.CONFIG
