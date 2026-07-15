"""Unit tests for Python mutation, documentation, and changelog detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.changelog import ChangelogKind, detect_changelog
from agentharness.plugins.python.documentation import (
    DocumentationKind,
    detect_documentation,
)
from agentharness.plugins.python.mutation import MutationKind, detect_mutation

_HERE = Path(__file__).parent.parent.parent.parent
PROJ = _HERE / "fixtures" / "python" / "project-quality"


class TestMutation:
    def test_mutmut_detected(self) -> None:
        result = detect_mutation(PROJ / "mutmut-project")
        assert result.kind == MutationKind.MUTMUT

    def test_no_mutation_returns_absent(self) -> None:
        result = detect_mutation(PROJ / "no-project-quality")
        assert result.kind == MutationKind.ABSENT


class TestDocumentation:
    def test_sphinx_detected(self) -> None:
        result = detect_documentation(PROJ / "sphinx-docs")
        assert result.kind == DocumentationKind.SPHINX

    def test_no_docs_returns_absent(self, tmp_path) -> None:
        result = detect_documentation(tmp_path)
        assert result.kind == DocumentationKind.ABSENT

    def test_readme_detected(self, tmp_path) -> None:
        (tmp_path / "README.md").write_text("# Project\n")
        result = detect_documentation(tmp_path)
        assert result.kind == DocumentationKind.README_ONLY


class TestChangelog:
    def test_no_changelog_returns_absent(self, tmp_path) -> None:
        result = detect_changelog(tmp_path)
        assert result.kind == ChangelogKind.ABSENT
