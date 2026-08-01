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
from agentharness.plugins.python.environment import EnvironmentKind, detect_environment
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


# `detect_logging` returns STDLIB as its FALLBACK — the value you get when
# no logging library is declared, not evidence that logging is configured.
# Counting it as present made discovery report "you have logging" for a
# project with none, which contradicts this module's verified-not-guessed
# contract and is exactly the false confidence that discredits an
# inventory. Only an explicitly declared library (structlog, loguru) is a
# finding. Handled here rather than in the plugin: "stdlib is always
# available in Python" may be a reasonable thing for other callers to
# hear — it just is not a configuration this tool should report as found.
_LOGGING_FALLBACK_KINDS = frozenset({"stdlib"})


def _detect_logging(root: Path) -> tuple[bool, str, tuple[str, ...]]:
    detection = detect_logging(root)
    if str(getattr(detection, "kind", _ABSENT)) in _LOGGING_FALLBACK_KINDS:
        # Phrased "library declared", not "configuration found", to match
        # the sibling messages' shape while staying accurate about what
        # was actually checked: logging is detected from declared
        # dependencies, not from a config file, and "no configuration
        # found" would send the owner looking for the wrong thing.
        return False, "No declared logging library found", ()
    return _detect_singleton(detection, "logging")


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


NOT_PYTHON_DETAIL = "Not applicable — not a Python project"


def is_python_project(root: Path) -> bool:
    """Does `root` carry a recognised Python marker?

    Every detector and scaffold in this module is Python-specific. Applied
    unconditionally they produce statements that are false about another
    language: a Go repo holding *_test.go files was told it had no test
    framework, offered adoption, and on apply received ruff.toml,
    pytest.ini and mypy.ini. Writing one language's tooling into another
    language's project is worse than reporting nothing at all.
    """
    if not root.is_dir():
        return False
    if detect_environment(root).kind is not EnvironmentKind.UNKNOWN:
        return True
    # A marker-less directory can still be Python — a loose script tree
    # with no packaging metadata is a real shape, and refusing to look at
    # it would be its own false negative.
    return any(root.glob("*.py")) or any(root.glob("*/*.py"))


def discover(root: Path | str) -> RepoInventory:
    """Inventory `root` read-only, one finding per capability in CAPABILITIES."""
    root_path = Path(root)
    findings: list[CapabilityFinding] = []

    if not is_python_project(root_path):
        # Report inapplicability rather than absence. "No linter
        # configured" is not a true statement about a Go repo — it is a
        # statement about a Python linter nobody asked for.
        return RepoInventory(
            root=str(root_path),
            capabilities=tuple(
                CapabilityFinding(c, False, NOT_PYTHON_DETAIL, ())
                for c in CAPABILITIES
            ),
        )

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
