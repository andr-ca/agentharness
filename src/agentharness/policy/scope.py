"""Policy scope expressions — path patterns and change classifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ScopeError(ValueError):
    """Raised when a scope expression is structurally invalid."""


class ChangeClass(StrEnum):
    """Semantic classification of what changed in a commit/push."""

    CODE = "code"
    DOCS = "docs"
    CONFIG = "config"
    TESTS = "tests"


@dataclass(frozen=True)
class PathExpression:
    """A glob pattern scoping a gate requirement to specific file paths.

    Patterns must be relative (no leading `/`) and must not contain `..`.
    """

    pattern: str

    def __post_init__(self) -> None:
        if not self.pattern:
            raise ScopeError("pattern must not be empty")
        if self.pattern.startswith("/"):
            raise ScopeError(
                f"absolute paths are not allowed in scope expressions: "
                f"{self.pattern!r}"
            )
        if ".." in self.pattern.split("/"):
            raise ScopeError(
                f"path traversal (..) is not allowed in scope expressions: "
                f"{self.pattern!r}"
            )


@dataclass(frozen=True)
class ScopeExpression:
    """A scope combining inclusion and exclusion path expressions.

    At least one include expression is required.
    """

    includes: list[PathExpression]
    excludes: list[PathExpression] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.includes:
            raise ScopeError(
                "at least one include expression is required in a scope"
            )
