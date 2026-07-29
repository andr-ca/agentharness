"""Tests for tools/context-budget.py — always-on context measurement.

The tool answers one question: how much context does a consuming session
pay before it does anything? Two properties matter more than precision.

*It must measure the right surfaces.* Always-on means loaded every
session regardless of task — the generated client routers, not the 35
on-demand skills. Measuring the wrong set would report a number nobody
can act on.

*It must gate on growth, not an absolute.* The root-instruction inventory
found that the largest section of the router is also the least safe to
cut, because it is prose-only-enforced. A threshold gate would point
straight at it. A growth gate stops silent bloat without demanding cuts
to guidance that is currently load-bearing.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "context-budget.py"
spec = importlib.util.spec_from_file_location("context_budget", MODULE_PATH)
cb = importlib.util.module_from_spec(spec)
# Registered before exec: @dataclass resolves its annotations via
# sys.modules[cls.__module__], which is None for a module loaded purely
# from a file spec.
sys.modules["context_budget"] = cb
spec.loader.exec_module(cb)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# --- what gets measured -----------------------------------------------


def test_measures_the_real_always_on_surfaces():
    surfaces = {s.name for s in cb.measure(REPO_ROOT)}

    # The generated client routers every session pays for.
    assert {"AGENTS.md", "GEMINI.md"} <= surfaces


def test_does_not_count_on_demand_skills_as_always_on():
    # 35 skills exist; only their descriptions are indexed, and the bodies
    # load on demand. Counting the bodies would inflate the number into
    # something nobody could act on.
    surfaces = {s.name for s in cb.measure(REPO_ROOT)}

    assert not any("skills/" in name for name in surfaces)


def test_reports_a_nonzero_total_for_this_repo():
    # Guards against the measurement silently matching nothing — the
    # failure mode where a green report means "never ran".
    report = cb.build_report(REPO_ROOT)

    assert report["total_tokens"] > 1000
    assert len(report["surfaces"]) >= 4


def test_a_missing_surface_is_reported_not_skipped(tmp_path):
    # A client file that disappears must show up as absent rather than
    # quietly shrinking the total, which would read as an improvement.
    report = cb.build_report(tmp_path)

    assert report["total_tokens"] == 0
    assert all(s["present"] is False for s in report["surfaces"])


# --- growth gating ----------------------------------------------------


def test_growth_within_tolerance_passes(tmp_path):
    baseline = {"total_tokens": 1000}
    assert cb.check_growth(1000, baseline, tolerance=0.05) == []
    assert cb.check_growth(1049, baseline, tolerance=0.05) == []


def test_growth_beyond_tolerance_fails(tmp_path):
    baseline = {"total_tokens": 1000}

    failures = cb.check_growth(1200, baseline, tolerance=0.05)

    assert len(failures) == 1
    assert "1200" in failures[0]
    assert "1000" in failures[0]


def test_shrinking_always_passes():
    # Reduction is the goal; never fail someone for achieving it.
    assert cb.check_growth(500, {"total_tokens": 1000}, tolerance=0.05) == []


def test_no_baseline_means_no_failure():
    # First run records rather than blocks — a gate that fails before a
    # baseline exists just teaches people to bypass it.
    assert cb.check_growth(9999, None, tolerance=0.05) == []


# --- baseline file ----------------------------------------------------


def test_baseline_roundtrips(tmp_path):
    path = tmp_path / "baseline.json"
    cb.write_baseline(path, {"total_tokens": 4242, "surfaces": []})

    assert cb.read_baseline(path)["total_tokens"] == 4242


def test_missing_baseline_reads_as_none(tmp_path):
    assert cb.read_baseline(tmp_path / "nope.json") is None


def test_corrupt_baseline_reads_as_none(tmp_path):
    # Treated as "no baseline" rather than crashing the gate: a damaged
    # record should not block every push until someone repairs it.
    path = _write(tmp_path, "baseline.json", "{not json")

    assert cb.read_baseline(path) is None


def test_report_is_json_serialisable():
    json.dumps(cb.build_report(REPO_ROOT))
