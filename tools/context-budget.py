#!/usr/bin/env python3
"""Measure the always-on context a consuming session is handed.

Every session pays for the generated client routers before it does
anything — and until now nothing measured that, so it could grow
indefinitely without anyone noticing. This reports the cost and, in CI,
fails when it *grows* beyond tolerance.

Why growth and not a threshold: the root-instruction inventory
(docs/operational/root-instruction-inventory-2026-07-28.md) found that
mechanical enforcement, not size, predicts what is safe to remove. The
largest section of the router is also the least safe to cut, because it
is prose-only-enforced — and it is what surfaced several real defects
that had no failing test. A gate demanding "get under N tokens" would
point straight at it. A growth gate stops silent bloat without demanding
cuts to guidance that is currently load-bearing.

Usage:
    python3 tools/context-budget.py                 # report (human)
    python3 tools/context-budget.py --json          # report (machine)
    python3 tools/context-budget.py --check         # fail on growth
    python3 tools/context-budget.py --update-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "docs/operational/context-budget-baseline.json"

# Default tolerance for growth before the gate fails. Generous enough that
# ordinary edits pass, tight enough that a new always-on section does not.
DEFAULT_TOLERANCE = 0.05

# The always-on surfaces: files a client loads every session regardless of
# task. Deliberately NOT the 35 skills — only their descriptions are
# indexed and their bodies load on demand, so counting them would inflate
# the number into something nobody can act on.
#
# CLAUDE.md is the source the others are generated from; it is counted
# because Claude Code loads it directly, and excluded from double-counting
# concerns because each client loads exactly one of these.
ALWAYS_ON_SURFACES: tuple[str, ...] = (
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".kilo/rules/agentharness.md",
)

# Cursor is the one client with a machine-readable always-on marker
# (`alwaysApply: true` frontmatter), so its surface is discovered rather
# than listed — if a rule is ever flipped to always-apply, this notices.
CURSOR_RULES_DIR = ".cursor/rules"


@dataclass(frozen=True)
class Surface:
    """One always-on context source and what it costs."""

    name: str
    present: bool
    bytes: int
    tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "present": self.present,
            "bytes": self.bytes,
            "tokens": self.tokens,
        }


def estimate_tokens(text: str) -> int:
    """Approximate token count.

    chars/4 is deliberately crude. The number is used for *relative*
    comparison against a baseline, where a consistent estimator matters far
    more than accuracy — and a real tokenizer would add a dependency and
    tie the figure to one vendor's model.
    """
    return len(text) // 4


def _always_apply_cursor_rules(root: Path) -> list[Path]:
    rules_dir = root / CURSOR_RULES_DIR
    if not rules_dir.is_dir():
        return []
    found = []
    for path in sorted(rules_dir.glob("*.mdc")):
        head = path.read_text(encoding="utf-8", errors="replace")[:400]
        if "alwaysApply: true" in head:
            found.append(path)
    return found


def measure(root: Path = REPO_ROOT) -> list[Surface]:
    """Measure every always-on surface, in a stable order."""
    surfaces: list[Surface] = []

    for rel in ALWAYS_ON_SURFACES:
        path = root / rel
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            surfaces.append(
                Surface(rel, True, len(text.encode("utf-8")), estimate_tokens(text))
            )
        else:
            # Reported as absent rather than skipped: a client file that
            # disappears must not quietly shrink the total, which would
            # read as an improvement.
            surfaces.append(Surface(rel, False, 0, 0))

    for path in _always_apply_cursor_rules(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel_name = path.relative_to(root).as_posix()
        surfaces.append(
            Surface(rel_name, True, len(text.encode("utf-8")), estimate_tokens(text))
        )

    return surfaces


def build_report(root: Path = REPO_ROOT) -> dict[str, Any]:
    surfaces = measure(root)
    return {
        "total_tokens": sum(s.tokens for s in surfaces),
        "total_bytes": sum(s.bytes for s in surfaces),
        "surfaces": [s.to_dict() for s in surfaces],
    }


def read_baseline(path: Path) -> dict[str, Any] | None:
    """The recorded baseline, or None when absent or unreadable.

    A damaged record reads as "no baseline" rather than raising: a
    corrupt file should not block every push until someone repairs it.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_baseline(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_growth(
    total: int,
    baseline: dict[str, Any] | None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[str]:
    """Failures if always-on context grew beyond tolerance.

    Shrinking always passes — reduction is the goal, and nobody should be
    failed for achieving it. No baseline also passes: a gate that fails
    before a baseline exists only teaches people to bypass it.
    """
    if baseline is None:
        return []
    previous = baseline.get("total_tokens")
    if not isinstance(previous, int) or previous <= 0:
        return []
    ceiling = int(previous * (1 + tolerance))
    if total <= ceiling:
        return []
    return [
        f"always-on context grew to {total} tokens from a baseline of "
        f"{previous} (ceiling {ceiling}, tolerance {tolerance:.0%}). "
        f"Reduce it, or run --update-baseline if the growth is intended."
    ]


def render_human(report: dict[str, Any]) -> str:
    lines = ["Always-on context budget", ""]
    width = max(len(s["name"]) for s in report["surfaces"])
    for surface in report["surfaces"]:
        marker = " " if surface["present"] else "!"
        lines.append(
            f"  {marker} {surface['name']:<{width}}  "
            f"{surface['tokens']:>6} tok"
            + ("" if surface["present"] else "   (absent)")
        )
    lines += ["", f"  TOTAL: {report['total_tokens']} tokens"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update-baseline", action="store_true", dest="update")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    args = parser.parse_args(argv)

    report = build_report(REPO_ROOT)

    if args.update:
        write_baseline(BASELINE_PATH, report)
        print(f"baseline updated: {report['total_tokens']} tokens")
        return 0

    print(json.dumps(report, indent=2, sort_keys=True) if args.as_json
          else render_human(report))

    if args.check:
        failures = check_growth(
            report["total_tokens"], read_baseline(BASELINE_PATH), args.tolerance
        )
        for failure in failures:
            print(f"\nFAIL: {failure}", file=sys.stderr)
        return 1 if failures else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
