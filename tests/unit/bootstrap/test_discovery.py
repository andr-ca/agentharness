"""Tests for the bootstrap discovery orchestrator.

Discovery answers one question per capability: does this repository
already do X, and what is the evidence? It composes the existing
read-only plugin detectors — it must not reimplement detection, and it
must never report a capability as present without a config file backing
it, because the whole first-run flow rests on telling the owner what is
verified versus what is only recommended.
"""

from __future__ import annotations

from pathlib import Path

from agentharness.bootstrap.discovery import (
    CAPABILITIES,
    discover,
)


def _write(root: Path, rel: str, content: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_empty_project_reports_every_capability_absent(tmp_path):
    inventory = discover(tmp_path)

    assert {c.capability for c in inventory.capabilities} == set(CAPABILITIES)
    assert all(not c.present for c in inventory.capabilities)


def test_detects_a_configured_linter(tmp_path):
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\nline-length = 88\n")

    inventory = discover(tmp_path)
    lint = inventory.capability("lint")

    assert lint.present
    assert "ruff" in lint.detail.lower()
    assert lint.evidence  # must cite where it was found


def test_detects_a_configured_test_framework(tmp_path):
    _write(tmp_path, "pyproject.toml", "[tool.pytest.ini_options]\naddopts = '-q'\n")

    assert discover(tmp_path).capability("test").present


def test_absent_capability_carries_no_false_evidence(tmp_path):
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\n")

    types = discover(tmp_path).capability("types")

    assert not types.present
    assert types.evidence == ()


def test_discovery_is_deterministic_for_the_same_tree(tmp_path):
    # The plan hash depends on this: same inputs must produce byte-identical
    # findings, or `apply --confirm <hash>` would spuriously reject a plan.
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\n[tool.pytest.ini_options]\n")

    assert discover(tmp_path) == discover(tmp_path)


def test_capabilities_are_reported_in_a_stable_order(tmp_path):
    order = [c.capability for c in discover(tmp_path).capabilities]

    assert order == list(CAPABILITIES)


def test_discovery_is_read_only(tmp_path):
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\n")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    discover(tmp_path)

    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after


def test_missing_root_does_not_raise(tmp_path):
    # A first run may point at a path that does not exist yet; report
    # everything absent rather than crashing the CLI.
    inventory = discover(tmp_path / "does-not-exist")

    assert all(not c.present for c in inventory.capabilities)
