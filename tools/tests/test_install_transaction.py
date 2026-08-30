"""Tests for install_transaction.py: state schema (currently v3),
collision classification, backups, preflight plan construction, the
crash journal used by harness-link.sh's existing-surface integration,
and copy-mode skill-update classification/hash tracking (skill_sources,
issue #300).
"""
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "setup" / "install_transaction.py"
spec = importlib.util.spec_from_file_location("install_transaction", MODULE_PATH)
it = importlib.util.module_from_spec(spec)
sys.modules["install_transaction"] = it
spec.loader.exec_module(it)


def test_load_state_migrates_v1_to_v3(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    state_path.write_text(json.dumps({"version": 1, "mode": "link", "skills": []}))
    data = it.load_state(state_path)
    assert data["schema_version"] == 3
    assert data["managed_blocks"] == []
    assert data["overwritten_files"] == []
    assert data["collision_decisions"] == []
    assert data["skill_sources"] == {}
    # v1 fields survive untouched
    assert data["mode"] == "link"


def test_load_state_missing_file_returns_fresh_skeleton(tmp_path):
    data = it.load_state(tmp_path / "does-not-exist.json")
    assert data["schema_version"] == 3
    assert data["managed_blocks"] == []
    assert data["skill_sources"] == {}


def test_load_state_migrates_v2_to_v3(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    original = {
        "schema_version": 2, "mode": "link", "skills": [],
        "managed_blocks": [{"file": "AGENTS.md", "block_id": "core-instructions",
                             "rendered_version": "0.2.1", "rendered_sha256": "abc"}],
        "overwritten_files": [], "collision_decisions": [],
    }
    state_path.write_text(json.dumps(original))
    data = it.load_state(state_path)
    assert data["schema_version"] == 3
    assert data["skill_sources"] == {}
    # v2 fields survive untouched
    assert data["managed_blocks"] == original["managed_blocks"]
    assert data["mode"] == "link"


def test_load_state_already_v3_is_passthrough(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    original = {
        "schema_version": 3, "mode": "link", "skills": [],
        "managed_blocks": [{"file": "AGENTS.md", "block_id": "core-instructions",
                             "rendered_version": "0.2.1", "rendered_sha256": "abc"}],
        "overwritten_files": [], "collision_decisions": [],
        "skill_sources": {"foo": "abc123"},
    }
    state_path.write_text(json.dumps(original))
    assert it.load_state(state_path) == original


def test_load_state_rejects_newer_schema_version(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    state_path.write_text(json.dumps({"schema_version": 4, "mode": "link"}))
    with pytest.raises(ValueError, match="schema_version"):
        it.load_state(state_path)


def test_load_state_rejects_boolean_schema_version(tmp_path):
    # JSON true/false are technically ints in Python (bool subclasses
    # int); True == 1 must not be silently accepted as version 1.
    state_path = tmp_path / ".agentharness-state.json"
    state_path.write_text(json.dumps({"schema_version": True, "mode": "link"}))
    with pytest.raises(ValueError, match="schema_version"):
        it.load_state(state_path)


def test_load_state_rejects_garbage_schema_version(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    state_path.write_text(json.dumps({"schema_version": "not-a-version", "mode": "link"}))
    with pytest.raises(ValueError, match="schema_version"):
        it.load_state(state_path)


def test_load_state_rejects_explicit_null_schema_version(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    state_path.write_text(json.dumps({"schema_version": None, "mode": "link"}))
    with pytest.raises(ValueError, match="schema_version"):
        it.load_state(state_path)


def test_save_state_writes_valid_json(tmp_path):
    state_path = tmp_path / ".agentharness-state.json"
    data = it.load_state(state_path)
    data["mode"] = "link"
    it.save_state(state_path, data)
    reloaded = json.loads(state_path.read_text())
    assert reloaded["mode"] == "link"
    assert reloaded["schema_version"] == 3


def _make_skill(base: Path, name: str, content: str = "hello") -> Path:
    skill_dir = base / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


def test_hash_dir_tree_stable_regardless_of_location(tmp_path):
    a = _make_skill(tmp_path / "a", "foo")
    b = _make_skill(tmp_path / "b", "foo")
    assert it.hash_dir_tree(a) == it.hash_dir_tree(b)


def test_hash_dir_tree_changes_with_content(tmp_path):
    a = _make_skill(tmp_path / "a", "foo", content="v1")
    before = it.hash_dir_tree(a)
    (a / "SKILL.md").write_text("v2")
    assert it.hash_dir_tree(a) != before


def test_classify_skill_updates_unrecorded_hash_treated_as_upstream_changed(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    _make_skill(source, "foo", content="upstream-v2")
    _make_skill(target, "foo", content="upstream-v1")
    result = it.classify_skill_updates(
        current=["foo"], to_add=[], source_path=source, target=target, skill_sources={},
    )
    assert result == {"to_refresh": ["foo"], "to_backup": []}


def test_classify_skill_updates_detects_local_edit(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    _make_skill(source, "foo", content="original")
    _make_skill(target, "foo", content="original")
    as_installed_hash = it.hash_dir_tree(target / ".claude" / "skills" / "foo")
    (target / ".claude" / "skills" / "foo" / "SKILL.md").write_text("consumer edited this")
    result = it.classify_skill_updates(
        current=["foo"], to_add=[], source_path=source, target=target,
        skill_sources={"foo": as_installed_hash},
    )
    assert result == {"to_refresh": [], "to_backup": ["foo"]}


def test_classify_skill_updates_recognizes_pure_upstream_drift(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    _make_skill(source, "foo", content="upstream-v2")
    _make_skill(target, "foo", content="original")
    as_installed_hash = it.hash_dir_tree(target / ".claude" / "skills" / "foo")
    result = it.classify_skill_updates(
        current=["foo"], to_add=[], source_path=source, target=target,
        skill_sources={"foo": as_installed_hash},
    )
    assert result == {"to_refresh": ["foo"], "to_backup": []}


def test_classify_skill_updates_skips_unchanged_and_to_add(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    _make_skill(source, "foo", content="same")
    _make_skill(target, "foo", content="same")
    _make_skill(source, "bar", content="new-skill")
    result = it.classify_skill_updates(
        current=["foo", "bar"], to_add=["bar"], source_path=source, target=target,
        skill_sources={},
    )
    assert result == {"to_refresh": [], "to_backup": []}


def test_apply_skill_sources_records_hash_for_refreshed_skill(tmp_path):
    target = tmp_path / "target"
    skill_dir = _make_skill(target, "foo", content="synced")
    state: dict[str, Any] = {"skill_sources": {}}
    it.apply_skill_sources(
        state=state, target=target, current=["foo"], to_remove=[], to_backup=[],
    )
    assert state["skill_sources"]["foo"] == it.hash_dir_tree(skill_dir)


def test_apply_skill_sources_preserves_backed_up_entry(tmp_path):
    target = tmp_path / "target"
    _make_skill(target, "foo", content="consumer edit")
    state: dict[str, Any] = {"skill_sources": {"foo": "original-hash-unchanged"}}
    it.apply_skill_sources(
        state=state, target=target, current=["foo"], to_remove=[], to_backup=["foo"],
    )
    assert state["skill_sources"]["foo"] == "original-hash-unchanged"


def test_apply_skill_sources_drops_removed_skill(tmp_path):
    target = tmp_path / "target"
    state: dict[str, Any] = {"skill_sources": {"foo": "x", "bar": "y"}}
    it.apply_skill_sources(
        state=state, target=target, current=[], to_remove=["bar"], to_backup=[],
    )
    assert "bar" not in state["skill_sources"]


def test_classify_path_block_managed_when_supported_instructions_file(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("# existing\n")
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.BLOCK_MANAGED


def test_classify_path_absent_file_is_block_managed_too(tmp_path):
    target = tmp_path / "AGENTS.md"
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.BLOCK_MANAGED


def test_classify_path_whole_file_collision_when_generated_surface_occupied(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer's own rule\n")
    result = it.classify_path(target, is_block_surface=False)
    assert result == it.Classification.WHOLE_FILE_COLLISION


def test_classify_path_absent_whole_file_surface_is_no_collision(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    assert it.classify_path(target, is_block_surface=False) == it.Classification.CREATE


def test_classify_path_symlink_is_hard_fail(tmp_path):
    real = tmp_path / "real.md"
    real.write_text("x\n")
    link = tmp_path / "AGENTS.md"
    link.symlink_to(real)
    assert it.classify_path(link, is_block_surface=True) == it.Classification.HARD_FAIL


def test_classify_path_directory_is_hard_fail(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.mkdir()
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.HARD_FAIL


def test_classify_path_malformed_markers_is_hard_fail(tmp_path):
    target = tmp_path / "AGENTS.md"
    content = (
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "no end\n"
    )
    target.write_text(content)
    result = it.classify_path(target, is_block_surface=True)
    assert result == it.Classification.HARD_FAIL


def test_backup_path_for_creates_unique_suffix(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("x\n")
    backup = it.backup_path_for(target, install_id="a1b2c3")
    assert backup.name == "testing.mdc.pre-agentharness.a1b2c3"


def test_reuse_existing_state_owned_backup_when_hash_matches(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("original\n")
    existing_backup = tmp_path / "rule.mdc.pre-agentharness.deadbeef"
    existing_backup.write_text("original\n")
    state = {"overwritten_files": [
        {"file": "rule.mdc",
         "backup": "rule.mdc.pre-agentharness.deadbeef",
         "written_sha256": "hash-of-whatever-harness-content-was-written",
         "backup_sha256": it.sha256_of_file(existing_backup)}
    ]}
    result = it.resolve_backup_path(
        target, state, install_id="newid", base_dir=tmp_path
    )
    assert result == existing_backup


def test_new_unique_backup_when_no_state_owned_backup_exists(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("x\n")
    state = {"overwritten_files": []}
    result = it.resolve_backup_path(
        target, state, install_id="newid", base_dir=tmp_path
    )
    assert result.name == "rule.mdc.pre-agentharness.newid"


def test_never_overwrites_existing_backup_file(tmp_path):
    target = tmp_path / "rule.mdc"
    target.write_text("x\n")
    collide = tmp_path / "rule.mdc.pre-agentharness.newid"
    collide.write_text("someone else's file\n")
    state = {"overwritten_files": []}
    result = it.resolve_backup_path(
        target, state, install_id="newid", base_dir=tmp_path
    )
    assert result != collide
    assert not result.exists()


def test_build_plan_reports_hard_fail_with_zero_mutations(tmp_path):
    target = tmp_path / "AGENTS.md"
    content = (
        "<!-- agentharness:begin id=core-instructions version=0.1.0 -->\n"
        "no end\n"
    )
    target.write_text(content)
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path,
        decide=lambda item: None
    )
    assert plan.ok is False
    assert plan.actions == []
    assert any("AGENTS.md" in e for e in plan.errors)


def test_build_plan_block_managed_surface_plans_upsert(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path,
        decide=lambda item: None
    )
    assert plan.ok is True
    assert len(plan.actions) == 1
    assert plan.actions[0].kind == "upsert_block"


def test_build_plan_whole_file_collision_calls_decide_callback(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]

    decisions = []
    def decide(item):
        decisions.append(item.path)
        return "overwrite"

    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=decide
    )
    assert plan.ok is True
    assert decisions == [target]
    assert plan.actions[0].kind == "overwrite_with_backup"


def test_build_plan_keep_existing_decision_skips_write(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path,
        decide=lambda item: "keep-existing"
    )
    assert plan.ok is True
    assert plan.actions == []


def test_build_plan_reuses_persisted_decision_when_hash_matches(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    state = {"collision_decisions": [
        {"item": ".cursor/rules/testing.mdc", "kind": "whole-file",
         "choice": "keep-existing",
         "existing_sha256": it.sha256_of_file(target),
         "decided_at": "2026-01-01T00:00:00Z"}
    ]}
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    called = []
    plan = it.build_plan(
        surfaces, state=state, install_id="x", base_dir=tmp_path,
        decide=lambda item: called.append(item) or "overwrite"
    )
    # decide() never invoked — persisted decision honored
    assert called == []
    assert plan.actions == []


def test_build_plan_stale_decision_recalls_decide(tmp_path):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("changed content\n")
    state = {"collision_decisions": [
        {"item": ".cursor/rules/testing.mdc", "kind": "whole-file",
         "choice": "keep-existing",
         "existing_sha256": "stale-hash-does-not-match",
         "decided_at": "2026-01-01T00:00:00Z"}
    ]}
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    called = []
    it.build_plan(
        surfaces, state=state, install_id="x", base_dir=tmp_path,
        decide=lambda item: called.append(item) or "keep-existing"
    )
    assert len(called) == 1


def test_apply_plan_writes_journal_and_leaves_it_for_the_caller(tmp_path):
    # apply_plan() itself must NOT delete the journal — only the caller,
    # after save_state() has actually persisted the updated state,
    # should do that (spec section 6's crash-consistency guarantee: a
    # crash between apply_plan() returning and save_state() completing
    # must still leave the journal behind for 'doctor' to find).
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=lambda i: None
    )
    journal_path = tmp_path / ".agentharness-state.pending.json"
    state = it.load_state(tmp_path / ".agentharness-state.json")
    it.apply_plan(
        plan, state=state, base_dir=tmp_path, journal_path=journal_path,
        install_id="x"
    )
    assert target.read_text().count("agentharness:begin") == 1
    assert journal_path.exists()


def test_cli_apply_removes_journal_only_after_save_state(tmp_path):
    import subprocess

    target = tmp_path / "AGENTS.md"
    surfaces_spec = tmp_path / "surfaces.json"
    surfaces_spec.write_text(json.dumps([
        {"path": str(target), "is_block_surface": True,
         "block_body": "rendered\n", "block_id": "core-instructions",
         "block_version": "0.2.1"}
    ]))
    journal_path = tmp_path / ".agentharness-state.pending.json"
    subprocess.run(
        [
            "python3", str(MODULE_PATH), "apply",
            "--surfaces", str(surfaces_spec),
            "--state", str(tmp_path / ".agentharness-state.json"),
            "--base-dir", str(tmp_path), "--install-id", "abc",
            "--journal", str(journal_path),
        ],
        capture_output=True, text=True, check=True,
    )
    assert not journal_path.exists()
    assert (tmp_path / ".agentharness-state.json").exists()


def test_apply_plan_records_managed_block_in_state(tmp_path):
    target = tmp_path / "AGENTS.md"
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=lambda i: None
    )
    state = it.load_state(tmp_path / ".agentharness-state.json")
    updated = it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="x"
    )
    assert len(updated["managed_blocks"]) == 1
    assert updated["managed_blocks"][0]["file"] == "AGENTS.md"


def test_apply_plan_overwrite_with_backup_records_backup_and_decision(
    tmp_path
):
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False,
        content="harness content\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="abc123", base_dir=tmp_path,
        decide=lambda i: "overwrite"
    )
    state = it.load_state(tmp_path / ".agentharness-state.json")
    updated = it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="abc123"
    )
    assert target.read_text() == "harness content\n"
    backup = tmp_path / ".cursor" / "rules" / "testing.mdc.pre-agentharness.abc123"
    assert backup.read_text() == "consumer content\n"
    assert len(updated["overwritten_files"]) == 1
    assert len(updated["collision_decisions"]) == 1
    decision = updated["collision_decisions"][0]
    assert decision["choice"] == "overwrite"
    # Regression: existing_sha256 must reflect the PRE-EXISTING consumer
    # content that caused the collision, not the harness content that
    # just got written — otherwise staleness checks and auditability
    # are meaningless.
    assert decision["existing_sha256"] == it.bi.sha256_bytes(
        b"consumer content\n"
    )


def test_apply_plan_repeated_overwrite_reuses_same_backup_not_a_new_one(
    tmp_path
):
    # Regression: resolve_backup_path() previously compared a backup
    # candidate's hash against written_sha256 (the harness-written
    # TARGET content's hash), which can never match a backup file (which
    # holds the original CONSUMER content) — so every repeated overwrite
    # minted a fresh .pre-agentharness.<id>-N file instead of reusing the
    # one already on disk.
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    state = it.load_state(tmp_path / ".agentharness-state.json")

    surfaces = [it.Surface(
        path=target, is_block_surface=False, content="harness content v1\n"
    )]
    plan = it.build_plan(
        surfaces, state=state, install_id="abc123", base_dir=tmp_path,
        decide=lambda i: "overwrite"
    )
    state = it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="abc123"
    )
    it.save_state(tmp_path / ".agentharness-state.json", state)
    first_backup = (
        tmp_path / ".cursor" / "rules" / "testing.mdc.pre-agentharness.abc123"
    )
    assert first_backup.read_text() == "consumer content\n"

    # Re-run with a different install_id (a later `update`/`init` call
    # gets a fresh install_id every time) and different harness content —
    # since target still isn't a persisted collision decision (this
    # state's collision_decisions won't match target's now-changed
    # content), the collision path runs again.
    surfaces2 = [it.Surface(
        path=target, is_block_surface=False, content="harness content v2\n"
    )]
    plan2 = it.build_plan(
        surfaces2, state=state, install_id="def456", base_dir=tmp_path,
        decide=lambda i: "overwrite"
    )
    state = it.apply_plan(
        plan2, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="def456"
    )

    # The ORIGINAL backup (still holding the true pre-harness consumer
    # content) must be reused — no second .pre-agentharness.* file.
    all_backups = list(
        (tmp_path / ".cursor" / "rules").glob("testing.mdc.pre-agentharness.*")
    )
    assert all_backups == [first_backup]
    assert first_backup.read_text() == "consumer content\n"
    assert target.read_text() == "harness content v2\n"


def test_build_plan_persists_keep_existing_decision_too(tmp_path):
    # Regression: build_plan()/apply_plan() previously only persisted a
    # collision_decisions entry for "overwrite" choices (inside
    # apply_plan's overwrite_with_backup branch) — "keep-existing" never
    # got recorded anywhere, so 'update' would re-prompt for the same
    # unchanged file every single run instead of honoring the earlier
    # answer.
    target = tmp_path / ".cursor" / "rules" / "testing.mdc"
    target.parent.mkdir(parents=True)
    target.write_text("consumer content\n")
    surfaces = [it.Surface(
        path=target, is_block_surface=False, content="harness content\n"
    )]
    state = it.load_state(tmp_path / ".agentharness-state.json")
    plan = it.build_plan(
        surfaces, state=state, install_id="x", base_dir=tmp_path,
        decide=lambda i: "keep-existing"
    )
    assert plan.actions == []
    assert len(plan.collision_decisions) == 1
    assert plan.collision_decisions[0]["choice"] == "keep-existing"
    assert plan.collision_decisions[0]["existing_sha256"] == it.bi.sha256_bytes(
        b"consumer content\n"
    )

    state = it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="x"
    )
    assert len(state["collision_decisions"]) == 1
    assert target.read_text() == "consumer content\n"  # untouched

    # A second run must now reuse the persisted decision without
    # re-invoking decide().
    called = []
    plan2 = it.build_plan(
        surfaces, state=state, install_id="y", base_dir=tmp_path,
        decide=lambda i: called.append(i) or "overwrite"
    )
    assert called == []
    assert plan2.actions == []


def test_journal_status_reports_leftover_journal(tmp_path):
    journal_path = tmp_path / ".agentharness-state.pending.json"
    journal_path.write_text(
        json.dumps(
            {"plan_summary": ["AGENTS.md: upsert_block"]}
        )
    )
    status = it.journal_status(journal_path)
    assert status["pending"] is True
    assert "AGENTS.md" in status["summary"][0]


def test_journal_status_clean_when_no_journal(tmp_path):
    status = it.journal_status(
        tmp_path / ".agentharness-state.pending.json"
    )
    assert status["pending"] is False


def test_cli_journal_status_via_subprocess(tmp_path):
    import subprocess

    journal_path = tmp_path / ".agentharness-state.pending.json"
    result = subprocess.run(
        [
            "python3",
            str(MODULE_PATH),
            "journal-status",
            "--journal",
            str(journal_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["pending"] is False


def test_rel_handles_relative_paths(tmp_path):
    # Regression test: _rel() should handle both absolute and relative paths
    # without raising ValueError (matches resolve_backup_path() behavior)
    rel_path = Path("cursor/rules/testing.mdc")
    result = it._rel(rel_path, tmp_path)
    assert result == "cursor/rules/testing.mdc"
    # Also verify absolute paths still work
    abs_path = tmp_path / "AGENTS.md"
    result = it._rel(abs_path, tmp_path)
    assert result == "AGENTS.md"


def test_cli_plan_reports_actions_via_subprocess(tmp_path):
    import subprocess

    surfaces_spec = tmp_path / "surfaces.json"
    surfaces_spec.write_text(
        json.dumps([
            {
                "path": str(tmp_path / "AGENTS.md"),
                "is_block_surface": True,
                "block_body": "rendered\n",
                "block_id": "core-instructions",
                "block_version": "0.2.1",
            }
        ])
    )
    result = subprocess.run(
        [
            "python3",
            str(MODULE_PATH),
            "plan",
            "--surfaces",
            str(surfaces_spec),
            "--state",
            str(tmp_path / ".agentharness-state.json"),
            "--base-dir",
            str(tmp_path),
            "--install-id",
            "abc",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["actions"][0]["kind"] == "upsert_block"


def test_cli_apply_writes_file_via_subprocess(tmp_path):
    import subprocess

    surfaces_spec = tmp_path / "surfaces.json"
    target = tmp_path / "AGENTS.md"
    surfaces_spec.write_text(
        json.dumps([
            {
                "path": str(target),
                "is_block_surface": True,
                "block_body": "rendered\n",
                "block_id": "core-instructions",
                "block_version": "0.2.1",
            }
        ])
    )
    result = subprocess.run(
        [
            "python3",
            str(MODULE_PATH),
            "apply",
            "--surfaces",
            str(surfaces_spec),
            "--state",
            str(tmp_path / ".agentharness-state.json"),
            "--base-dir",
            str(tmp_path),
            "--install-id",
            "abc",
            "--journal",
            str(tmp_path / ".agentharness-state.pending.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "agentharness:begin" in target.read_text()


def test_apply_plan_creates_parent_dirs_for_upsert_block(tmp_path):
    # Regression test: upsert_block should create parent directories
    # (e.g., .github/) if they don't exist yet
    target = tmp_path / ".github" / "copilot-instructions.md"
    assert not (tmp_path / ".github").exists()
    surfaces = [it.Surface(
        path=target, is_block_surface=True, block_body="rendered\n"
    )]
    plan = it.build_plan(
        surfaces, state={"collision_decisions": []},
        install_id="x", base_dir=tmp_path, decide=lambda i: None
    )
    state = it.load_state(tmp_path / ".agentharness-state.json")
    it.apply_plan(
        plan, state=state, base_dir=tmp_path,
        journal_path=tmp_path / ".agentharness-state.pending.json",
        install_id="x"
    )
    assert target.exists()
    assert "agentharness:begin" in target.read_text()


def test_uninstall_all_removes_block_and_restores_backup(tmp_path: Any) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "keep me\n\n<!-- agentharness:begin id=core-instructions version=0.2.1 "
        "-->\nbody\n<!-- agentharness:end id=core-instructions -->\n"
    )
    rule = tmp_path / "rule.mdc"
    rule.write_text("harness content\n")
    backup = tmp_path / "rule.mdc.pre-agentharness.abc"
    backup.write_text("consumer original\n")

    state: dict[str, Any] = {
        "managed_blocks": [
            {
                "file": "AGENTS.md",
                "block_id": "core-instructions",
                "rendered_version": "0.2.1",
                "rendered_sha256": "x",
            }
        ],
        "overwritten_files": [
            {
                "file": "rule.mdc",
                "backup": "rule.mdc.pre-agentharness.abc",
                "written_sha256": it.sha256_of_file(rule),
            }
        ],
        "collision_decisions": [],
    }
    it.uninstall_all(state, base_dir=tmp_path)
    assert "keep me" in agents.read_text()
    assert "agentharness:begin" not in agents.read_text()
    assert rule.read_text() == "consumer original\n"
    assert state["managed_blocks"] == []
    assert state["overwritten_files"] == []


def test_uninstall_all_leaves_edited_file_and_warns(tmp_path: Any) -> None:
    rule = tmp_path / "rule.mdc"
    rule.write_text("edited after install\n")
    state: dict[str, Any] = {
        "managed_blocks": [],
        "overwritten_files": [
            {
                "file": "rule.mdc",
                "backup": "rule.mdc.pre-agentharness.abc",
                "written_sha256": "does-not-match-current-content",
            }
        ],
        "collision_decisions": [],
    }
    log = it.uninstall_all(state, base_dir=tmp_path)
    assert rule.read_text() == "edited after install\n"
    assert any("edited" in line for line in log)


# ---------------------------------------------------------------------------
# uninstall must not leave 0-byte husks. When install CREATES an instructions
# file, that file holds nothing but the managed block; stripping the block
# leaves an empty CLAUDE.md/AGENTS.md/GEMINI.md behind, which reads as
# "configured" to a human and to some tools. Found by running a full
# install -> update -> uninstall journey against a real project.
#
# Emptiness alone is NOT a safe discriminator, which the first version of
# this fix got wrong: a user can have a pre-existing EMPTY instructions file
# (touch CLAUDE.md as a placeholder), and deleting it on uninstall is data
# loss. Deletion is therefore gated on recorded provenance —
# created_by_harness, captured at install time — with emptiness as a second
# condition, and anything unknown left in place.
# ---------------------------------------------------------------------------


def _block(body: str = "harness content") -> str:
    # Real marker syntax, per block_installer's _BEGIN_RE/_END_RE. An
    # invented one would make remove_block a no-op and these tests would
    # pass or fail for reasons unrelated to what they name.
    return (
        "<!-- agentharness:begin id=core-instructions version=abc123 -->\n"
        f"{body}\n"
        "<!-- agentharness:end id=core-instructions -->\n"
    )


def _state(file_name: str, created: bool | None = True) -> dict:
    entry: dict = {"file": file_name, "block_id": "core-instructions"}
    if created is not None:
        entry["created_by_harness"] = created
    return {"managed_blocks": [entry], "overwritten_files": []}


def test_uninstall_removes_a_file_that_held_only_the_block(tmp_path):
    path = tmp_path / "CLAUDE.md"
    path.write_text(_block())

    log = it.uninstall_all(_state("CLAUDE.md"), tmp_path)

    assert not path.exists(), "an install-created file must not survive as a husk"
    assert any("removed" in line for line in log)


def test_uninstall_keeps_a_file_the_user_already_had(tmp_path):
    # The load-bearing counter-case: their content must survive.
    path = tmp_path / "CLAUDE.md"
    path.write_text("# My own project rules\n\n" + _block())

    it.uninstall_all(_state("CLAUDE.md"), tmp_path)

    assert path.exists()
    assert "My own project rules" in path.read_text()
    assert "harness content" not in path.read_text()


def test_uninstall_removes_a_file_left_with_only_whitespace(tmp_path):
    # Block removal can leave stray newlines; whitespace is still empty.
    path = tmp_path / "AGENTS.md"
    path.write_text("\n\n" + _block() + "\n")

    it.uninstall_all(_state("AGENTS.md"), tmp_path)

    assert not path.exists()


def test_uninstall_leaves_an_untouched_file_alone(tmp_path):
    # No block present: nothing was ours, so nothing is removed.
    path = tmp_path / "CLAUDE.md"
    path.write_text("# Not ours\n")

    it.uninstall_all(_state("CLAUDE.md"), tmp_path)

    assert path.exists()
    assert path.read_text() == "# Not ours\n"


def test_uninstall_keeps_a_preexisting_empty_file(tmp_path):
    # The data-loss case the emptiness-only rule missed: the user touched
    # CLAUDE.md as a placeholder, install added its block. Their file is
    # still theirs, however little is in it.
    path = tmp_path / "CLAUDE.md"
    path.write_text(_block())

    it.uninstall_all(_state("CLAUDE.md", created=False), tmp_path)

    assert path.exists(), "a file the user created must never be deleted"
    assert path.read_text().strip() == ""


def test_uninstall_keeps_a_file_with_no_recorded_provenance(tmp_path):
    # State written before provenance existed. Unknown must mean "leave
    # it" — an old install must not become a delete on upgrade.
    path = tmp_path / "CLAUDE.md"
    path.write_text(_block())

    it.uninstall_all(_state("CLAUDE.md", created=None), tmp_path)

    assert path.exists()


def test_uninstall_deletes_only_when_provenance_says_we_made_it(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(_block())

    it.uninstall_all(_state("AGENTS.md", created=True), tmp_path)

    assert not path.exists()


def test_uninstall_survives_the_file_vanishing_mid_run(tmp_path):
    # Concurrent cleanup between the read and the unlink must not crash
    # the whole uninstall and strand the remaining entries.
    path = tmp_path / "AGENTS.md"
    path.write_text(_block())
    state = _state("AGENTS.md", created=True)

    original_unlink = Path.unlink

    def vanishing_unlink(self, **kwargs):
        original_unlink(self, **kwargs)
        return original_unlink(self, **kwargs)  # second call: already gone

    Path.unlink = vanishing_unlink
    try:
        it.uninstall_all(state, tmp_path)
    finally:
        Path.unlink = original_unlink

    assert not path.exists()


def test_uninstall_removes_a_directory_left_empty_by_deleting_our_file(tmp_path):
    nested = tmp_path / ".github"
    nested.mkdir()
    (nested / "copilot-instructions.md").write_text(_block())

    it.uninstall_all(_state(".github/copilot-instructions.md"), tmp_path)

    assert not nested.exists(), "an empty .github/ husk must not be left behind"


def test_uninstall_keeps_a_directory_holding_anything_else(tmp_path):
    nested = tmp_path / ".github"
    (nested / "workflows").mkdir(parents=True)
    (nested / "workflows" / "ci.yml").write_text("name: ci\n")
    (nested / "copilot-instructions.md").write_text(_block())

    it.uninstall_all(_state(".github/copilot-instructions.md"), tmp_path)

    assert (nested / "workflows" / "ci.yml").exists()


def test_prune_never_climbs_above_the_project_root(tmp_path):
    # The safety property: an uninstall must not be able to delete
    # directories outside the project, however empty they are.
    #
    # Must start the walk *below* the root and let it climb: passing the
    # root as both arguments makes the loop condition false on the first
    # evaluation, so the body never runs and the test proves nothing about
    # the guard it names.
    outer = tmp_path / "outer"
    project = outer / "project"
    nested = project / "a" / "b"
    nested.mkdir(parents=True)

    it._prune_empty_parents(nested, project)

    assert not (project / "a").exists(), "empty dirs below the root are pruned"
    assert project.exists(), "the prune must stop at the project root"
    assert outer.exists(), "the prune must never escape the project"
