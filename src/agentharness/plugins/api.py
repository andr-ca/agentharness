"""Plugin API contract types.

All objects returned by a plugin must conform to these types.
The runner validates every returned value before passing it to the core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FindingCode(StrEnum):
    """Stable result codes for plugin findings."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class PluginError(RuntimeError):
    """Raised by plugins to signal a structured failure."""


@dataclass(frozen=True)
class PluginMetadata:
    """Versioned metadata declared by every plugin.

    All fields are stable identifiers validated at registration time.
    """

    plugin_id: str
    display_name: str
    version: str
    capabilities: list[str]
    core_version_range: str

    def __post_init__(self) -> None:
        if not self.plugin_id:
            raise ValueError("plugin_id must not be empty")
        if not self.capabilities:
            raise ValueError("capabilities must not be empty")
        if not self.version:
            raise ValueError("version must not be empty")
        if not self.core_version_range:
            raise ValueError("core_version_range must not be empty")


@dataclass(frozen=True)
class Finding:
    """A single finding produced by a plugin check.

    capability: the stable capability ID this finding covers.
    code:       one of the FindingCode values.
    summary:    a human-readable one-line description.
    evidence:   arbitrary, structured, serialisable supporting data.
                Must not contain secrets or credentials.
    """

    capability: str
    code: FindingCode
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckResult:
    """The structured result returned by a plugin's check() method."""

    plugin_id: str
    findings: list[Finding]
