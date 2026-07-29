"""Repository discovery for the first-run bootstrap flow.

Answers one question per capability: does this repository already do X,
and what is the evidence? Composes the existing read-only detectors under
`agentharness.plugins` rather than reimplementing detection, so the
bootstrap surface and the plugin checks can never disagree about what a
project has.

Two properties the rest of the flow depends on:

*Verified, not guessed.* A capability is reported present only when a
configuration file says so. The interview presents detections as facts
and everything else as recommendations, and that distinction is
worthless if presence is inferred.

*Deterministic.* The same tree must produce byte-identical findings in a
stable order, because the plan hash is computed over them — a wobbling
inventory would make `apply --confirm <hash>` reject valid plans.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentharness.plugins.python.documentation import detect_documentation
from agentharness.plugins.python.linting import detect_lint_tools
from agentharness.plugins.python.logging import detect_logging
from agentharness.plugins.python.mutation import detect_mutation
from agentharness.plugins.python.testing import detect_test_frameworks
from agentharness.plugins.python.typing import detect_typing_tools

# Stable, ordered capability ids. Order is part of the contract: it fixes
# the order of `RepoInventory.capabilities`, which the plan hash covers.
CAPABILITIES: tuple[str, ...] = (
    "lint",
    "test",
    "types",
    "logging",
    "docs",
    "mutation",
)

# Human-facing labels, kept next to the ids so the CLI and the skill
# describe capabilities identically.
CAPABILITY_LABELS: dict[str, str] = {
    "lint": "Linting / formatting",
    "test": "Test framework",
    "types": "Static type checking",
    "logging": "Structured logging",
    "docs": "Documentation tooling",
    "mutation": "Mutation testing",
}


@dataclass(frozen=True)
class CapabilityFinding:
    """What was found for one capability.

    `present` is true only with config-file evidence. `evidence` lists the
    files that establish it, and is empty whenever `present` is false —
    absent capabilities must not carry partial evidence that could read
    as a weak positive.
    """

    capability: str
    present: bool
    detail: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepoInventory:
    """The full read-only picture of one repository root."""

    root: str
    capabilities: tuple[CapabilityFinding, ...]

    def capability(self, capability_id: str) -> CapabilityFinding:
        for finding in self.capabilities:
            if finding.capability == capability_id:
                return finding
        raise KeyError(f"unknown capability: {capability_id}")

    @property
    def present(self) -> tuple[str, ...]:
        return tuple(c.capability for c in self.capabilities if c.present)

    @property
    def absent(self) -> tuple[str, ...]:
        return tuple(c.capability for c in self.capabilities if not c.present)


def _from_tool_list(
    tools: list[Any], label: str
) -> tuple[bool, str, tuple[str, ...]]:
    """Normalise the `list[X]` detectors, which share `kind`/`config_source`."""
    if not tools:
        return False, f"No {label} configuration found", ()
    kinds = sorted({str(t.kind) for t in tools})
    sources = tuple(
        sorted(
            str(t.config_source)
            for t in tools
            if getattr(t, "config_source", None)
        )
    )
    return True, ", ".join(kinds), sources


def _detect_lint(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    return _from_tool_list(detect_lint_tools(root), "linter")


def _detect_test(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    return _from_tool_list(detect_test_frameworks(root), "test framework")


def _detect_types(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    return _from_tool_list(detect_typing_tools(root), "type checker")


# Every single-object detector spells "nothing found" the same way.
_ABSENT = "absent"


def _detect_singleton(
    detection: object, label: str
) -> tuple[bool, str, tuple[str, ...]]:
    """Normalise the single-object detectors, which expose only `kind`."""
    kind = str(getattr(detection, "kind", _ABSENT))
    if not kind or kind == _ABSENT:
        return False, f"No {label} configuration found", ()
    return True, kind, ()


def _detect_logging(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    return _detect_singleton(detect_logging(root), "logging")


def _detect_docs(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    return _detect_singleton(detect_documentation(root), "documentation")


def _detect_mutation(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    return _detect_singleton(detect_mutation(root), "mutation testing")


_DETECTORS: dict[str, Callable[[Path], tuple[bool, str, tuple[str, ...]]]] = {
    "lint": _detect_lint,
    "test": _detect_test,
    "types": _detect_types,
    "logging": _detect_logging,
    "docs": _detect_docs,
    "mutation": _detect_mutation,
}


def discover(root: Path | str) -> RepoInventory:
    """Inventory `root` read-only, one finding per capability in CAPABILITIES."""
    root_path = Path(root)
    findings: list[CapabilityFinding] = []

    for capability in CAPABILITIES:
        detector = _DETECTORS[capability]
        present: bool
        detail: str
        evidence: tuple[str, ...]
        if not root_path.is_dir():
            # A first run can legitimately point at a path that does not
            # exist yet. Report everything absent instead of raising —
            # "nothing here" is a valid, useful answer for bootstrap.
            present, detail, evidence = False, "Path does not exist", ()
        else:
            try:
                present, detail, evidence = detector(root_path)
            except Exception as exc:  # noqa: BLE001 - one bad detector must
                # not abort the whole inventory; report it as absent with
                # the reason, so the owner still gets every other finding.
                present, detail, evidence = False, f"Detection failed: {exc}", ()
        findings.append(
            CapabilityFinding(
                capability=capability,
                present=present,
                detail=detail,
                evidence=evidence,
            )
        )

    return RepoInventory(root=str(root_path), capabilities=tuple(findings))
