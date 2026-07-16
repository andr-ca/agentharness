"""Unit tests for policy scope expressions."""

from __future__ import annotations

import pytest

from agentharness.policy.scope import (
    ChangeClass,
    PathExpression,
    ScopeError,
    ScopeExpression,
)


class TestPathExpression:
    def test_basic_glob_pattern(self) -> None:
        expr = PathExpression("src/**/*.py")
        assert expr.pattern == "src/**/*.py"

    def test_empty_pattern_raises(self) -> None:
        with pytest.raises(ScopeError, match="pattern"):
            PathExpression("")

    def test_path_traversal_rejected(self) -> None:
        with pytest.raises(ScopeError, match="traversal"):
            PathExpression("../secret.env")

    def test_absolute_path_rejected(self) -> None:
        with pytest.raises(ScopeError, match="absolute"):
            PathExpression("/etc/passwd")


class TestChangeClass:
    def test_known_classes(self) -> None:
        for cls in ("code", "docs", "config", "tests"):
            assert ChangeClass(cls).value == cls

    def test_unknown_class_raises(self) -> None:
        with pytest.raises(ValueError):
            ChangeClass("unknown-class")


class TestScopeExpression:
    def test_include_and_exclude(self) -> None:
        scope = ScopeExpression(
            includes=[PathExpression("src/**")],
            excludes=[PathExpression("src/generated/**")],
        )
        assert len(scope.includes) == 1
        assert len(scope.excludes) == 1

    def test_empty_includes_raises(self) -> None:
        with pytest.raises(ScopeError, match="include"):
            ScopeExpression(includes=[], excludes=[])

    def test_is_deterministic(self) -> None:
        s1 = ScopeExpression(includes=[PathExpression("src/**")])
        s2 = ScopeExpression(includes=[PathExpression("src/**")])
        assert s1 == s2
