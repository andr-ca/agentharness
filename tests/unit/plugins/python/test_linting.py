"""Unit tests for Python linting and formatting tool detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.linting import (
    LintToolKind,
    detect_lint_tools,
)

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "python" / "quality"  # noqa: E501


class TestDetectLintTools:
    def test_ruff_only(self) -> None:
        tools = detect_lint_tools(FIXTURES / "ruff-only")
        kinds = {t.kind for t in tools}
        assert LintToolKind.RUFF in kinds

    def test_black_only(self) -> None:
        tools = detect_lint_tools(FIXTURES / "black-only")
        kinds = {t.kind for t in tools}
        assert LintToolKind.BLACK in kinds

    def test_ruff_and_mypy(self) -> None:
        tools = detect_lint_tools(FIXTURES / "ruff-and-mypy")
        kinds = {t.kind for t in tools}
        assert LintToolKind.RUFF in kinds

    def test_no_quality_tools_returns_empty(self) -> None:
        tools = detect_lint_tools(FIXTURES / "no-quality-tools")
        assert tools == []

    def test_detection_is_deterministic(self) -> None:
        path = FIXTURES / "ruff-and-mypy"
        run1 = detect_lint_tools(path)
        run2 = detect_lint_tools(path)
        assert [t.kind for t in run1] == [t.kind for t in run2]

    def test_detection_does_not_mutate_project(self, tmp_path) -> None:
        before = set(tmp_path.rglob("*"))
        detect_lint_tools(tmp_path)
        after = set(tmp_path.rglob("*"))
        assert before == after


def test_detects_ruff_from_its_own_standalone_config(tmp_path):
    # ruff.toml and .ruff.toml are ruff's own documented config files, not
    # an agentharness invention. Detection previously only looked inside
    # pyproject.toml, so a project configured the standard standalone way
    # was reported as having no linter at all.
    (tmp_path / "ruff.toml").write_text("line-length = 88\n", encoding="utf-8")

    tools = detect_lint_tools(tmp_path)

    assert [t.kind for t in tools] == [LintToolKind.RUFF]
    assert tools[0].config_source == "ruff.toml"


def test_detects_ruff_from_the_dotfile_variant(tmp_path):
    (tmp_path / ".ruff.toml").write_text("line-length = 88\n", encoding="utf-8")

    assert [t.kind for t in detect_lint_tools(tmp_path)] == [LintToolKind.RUFF]


def test_standalone_ruff_config_does_not_double_count_with_pyproject(tmp_path):
    (tmp_path / "ruff.toml").write_text("line-length = 88\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")

    assert [t.kind for t in detect_lint_tools(tmp_path)] == [LintToolKind.RUFF]
