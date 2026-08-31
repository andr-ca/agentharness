"""Preflight planning, collision classification, and crash-safe apply
for harness-link.sh's existing-surface integration. Orchestrates
block_installer.py; owns state schema (currently v3, which added
skill_sources -- an as-installed content-hash map used to distinguish a
consumer's local edit to a copy-mode skill from an upstream change; see
GitHub issue #300). See
docs/superpowers/specs/2026-07-17-existing-surface-integration-design.md.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import block_installer as bi  # noqa: E402

SCHEMA_VERSION = 3

_V2_LIST_FIELDS = ("managed_blocks", "overwritten_files", "collision_decisions")
_V3_DICT_FIELDS = ("skill_sources",)


def _fresh_state_skeleton() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        **{k: [] for k in _V2_LIST_FIELDS},
        **{k: {} for k in _V3_DICT_FIELDS},
    }


def load_state(path: Path) -> dict[str, Any]:
    """Load state, migrating legacy v1 -> v2 -> v3 in memory (schema
    migration policy tracked as F-12; each step only adds that
    version's new fields via setdefault, never rewrites fields an
    earlier version already wrote). Missing file returns a fresh
    skeleton at SCHEMA_VERSION with no other fields — callers merge in
    mode/skills/etc. themselves.

    The only recognized "old" shape with no schema_version key at all
    is legacy v1 -- an explicit schema_version key, even JSON null,
    does not qualify. Any *known*, older-than-current schema_version
    (currently: 1 through SCHEMA_VERSION - 1) migrates forward. Any
    *unrecognized* schema_version -- newer than SCHEMA_VERSION, or
    something that was never a real version at all (garbage, an
    explicit null) -- raises rather than being silently coerced to
    SCHEMA_VERSION and overwritten in place on the next save_state()."""
    path = Path(path)
    if not path.exists():
        return _fresh_state_skeleton()
    data: dict[str, Any] = json.loads(path.read_text())
    version: Any = data["schema_version"] if "schema_version" in data else 1
    if version == SCHEMA_VERSION:
        return data
    is_known_old = isinstance(version, int) and not isinstance(version, bool)
    if not is_known_old or not (1 <= version < SCHEMA_VERSION):
        raise ValueError(
            f"{path}: unrecognized schema_version {version!r} (this tool "
            f"understands schema_version 1 through {SCHEMA_VERSION}) -- "
            "refusing to silently overwrite it. This state file was "
            "likely written by a newer or incompatible version of "
            "agentharness; upgrade before operating on it."
        )
    for f in _V2_LIST_FIELDS:
        data.setdefault(f, [])
    for f in _V3_DICT_FIELDS:
        data.setdefault(f, {})
    data["schema_version"] = SCHEMA_VERSION
    return data


def save_state(path: Path, data: dict[str, Any]) -> None:
    path = Path(path)
    path.write_text(json.dumps(data, indent=2) + "\n")


def hash_dir_tree(path: Path) -> str:
    """Deterministic sha256 over a directory's files (relative paths and
    content), stable regardless of the directory's absolute location or
    the filesystem's iteration order. Used to detect a consumer's local
    edit to an installed copy-mode skill: compare this hash of the
    skill's current on-disk content against the hash recorded at the
    last (re-)install of that skill."""
    h = hashlib.sha256()
    files = (p for p in path.rglob("*") if p.is_file())
    for rel in sorted(p.relative_to(path).as_posix() for p in files):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((path / rel).read_bytes())
        h.update(b"\0")
    return h.hexdigest()


class Classification(Enum):
    CREATE = auto()               # nothing there yet, write it
    BLOCK_MANAGED = auto()        # supported instructions file: insert/replace block
    WHOLE_FILE_COLLISION = auto() # generated whole-file surface already occupied
    HARD_FAIL = auto()            # malformed markers, symlink, or non-regular file


def classify_path(
    path: Path, *, is_block_surface: bool, harness_owned: bool = False
) -> Classification:
    """Classify a target path per spec section 4's three-way rule.
    is_block_surface=True for CLAUDE.md/AGENTS.md/GEMINI.md/copilot
    files (block-managed); False for directory-style generated assets
    like .cursor/rules/*.mdc (whole-file collision candidates).

    harness_owned=True means the caller already confirmed, via state,
    that this exact path was last written by the harness itself and is
    still byte-identical to that write — e.g. AGENTS.md under the codex
    client, re-run on a plain `update` with no skill/content changes.
    Without this, every whole-file surface would present itself as an
    unresolved WHOLE_FILE_COLLISION on the very next run after the one
    that created it, since classification is otherwise a pure
    filesystem check with no memory of who wrote what: a harness-owned,
    untouched file should refresh silently like a block surface does,
    while a hand-edited or genuinely foreign file must still stop for
    collision resolution."""
    path = Path(path)

    if path.is_symlink():
        return Classification.HARD_FAIL
    if path.exists() and not path.is_file():
        return Classification.HARD_FAIL

    if not path.exists():
        return (
            Classification.BLOCK_MANAGED
            if is_block_surface
            else Classification.CREATE
        )

    if is_block_surface:
        try:
            bi.find_blocks(path.read_text(), "core-instructions")
        except bi.MarkerError:
            return Classification.HARD_FAIL
        return Classification.BLOCK_MANAGED

    if harness_owned:
        return Classification.CREATE

    return Classification.WHOLE_FILE_COLLISION


def sha256_of_file(path: Path) -> str:
    return bi.sha256_bytes(Path(path).read_bytes())


def backup_path_for(target: Path, install_id: str) -> Path:
    return target.with_name(f"{target.name}.pre-agentharness.{install_id}")


def resolve_backup_path(
    target: Path,
    state: dict[str, Any],
    install_id: str,
    base_dir: Path,
) -> Path:
    """Collision-safe backup resolution (spec section 4):
    - reuse a state-owned backup if its recorded hash still matches its
      own on-disk content (it already holds true pre-harness bytes);
    - otherwise mint a new unique '<name>.pre-agentharness.<install_id>'
      path, generating a fresh suffix if that exact path is already
      occupied by something this state doesn't own — never overwritten.
    """
    rel = (
        str(target.relative_to(base_dir)) if target.is_absolute()
        else str(target)
    )
    for entry in state.get("overwritten_files", []):
        if entry["file"] != rel:
            continue
        backup_path: str = entry.get("backup", "")
        existing_backup = base_dir / backup_path
        # Compare against backup_sha256 (the hash of what the backup
        # itself holds — the pre-existing consumer content that was
        # copied into it), not written_sha256 (the hash of the harness
        # content written to the TARGET) — those are hashes of two
        # different files and would essentially never match.
        if (
            existing_backup.exists()
            and sha256_of_file(existing_backup) == entry.get("backup_sha256")
        ):
            return existing_backup

    candidate = backup_path_for(target, install_id)
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = backup_path_for(target, f"{install_id}-{suffix}")
    return candidate


@dataclass
class Surface:
    path: Path
    is_block_surface: bool
    block_body: str = ""
    content: str = ""
    block_id: str = "core-instructions"
    block_version: str = "0.0.0"
    client: str = ""  # generating client (codex, cursor, etc); empty for core


@dataclass
class PlanItem:
    path: Path


@dataclass
class Action:
    kind: str
    surface: Surface


@dataclass
class Plan:
    ok: bool
    actions: list[Action] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    collision_decisions: list[dict[str, Any]] = field(default_factory=list)


def _rel(path: Path, base_dir: Path) -> str:
    path = Path(path)
    return str(path.relative_to(base_dir)) if path.is_absolute() else str(path)


def _find_decision(
    state: dict[str, Any], rel_path: str, target: Path
) -> str | None:
    for entry in state.get("collision_decisions", []):
        if entry["item"] != rel_path:
            continue
        existing_sha = entry.get("existing_sha256")
        if existing_sha == sha256_of_file(target):
            choice: str | None = entry.get("choice")
            return choice
        return None  # stale — caller must re-decide
    return None


def build_plan(
    surfaces: list[Surface],
    state: dict[str, Any],
    install_id: str,
    base_dir: Path,
    decide: Callable[[PlanItem], str],
) -> Plan:
    """Discover -> validate -> resolve decisions -> construct plan.
    Fails the whole plan (zero actions) if any surface hard-fails
    classification, per spec section 6's zero-mutation guarantee."""
    errors: list[str] = []
    actions: list[Action] = []
    collision_decisions: list[dict[str, Any]] = []

    for surface in surfaces:
        harness_owned = False
        if not surface.is_block_surface and surface.path.exists():
            rel_for_ownership = _rel(surface.path, base_dir)
            prior_owned = next(
                (
                    f
                    for f in state.get("overwritten_files", [])
                    if f["file"] == rel_for_ownership
                ),
                None,
            )
            harness_owned = bool(
                prior_owned
                and prior_owned.get("created_by_harness") is True
                and prior_owned.get("written_sha256")
                == sha256_of_file(surface.path)
            )
        classification = classify_path(
            surface.path,
            is_block_surface=surface.is_block_surface,
            harness_owned=harness_owned,
        )

        if classification is Classification.HARD_FAIL:
            errors.append(
                f"{surface.path}: malformed markers or unsafe target"
            )
            continue
        if errors:
            continue  # stop planning actions once any surface has failed

        if classification is Classification.BLOCK_MANAGED:
            actions.append(Action(kind="upsert_block", surface=surface))
        elif classification is Classification.CREATE:
            actions.append(Action(kind="create", surface=surface))
        elif classification is Classification.WHOLE_FILE_COLLISION:
            rel_path = _rel(surface.path, base_dir)
            persisted_choice = _find_decision(state, rel_path, surface.path)
            if persisted_choice is not None:
                choice = persisted_choice
                # Already recorded and still valid (hash matched) — no
                # new collision_decisions entry needed.
            else:
                # Capture the hash of what's on disk RIGHT NOW, before
                # any mutation — this is the pre-existing consumer
                # content that caused the collision, which is what a
                # later run's staleness check must compare against.
                # Capturing it here (at plan time) rather than in
                # apply_plan means it's correct for BOTH "overwrite"
                # (where apply_plan is about to replace the file with
                # harness content) and "keep-existing" (where nothing
                # ever gets written, so there'd be nothing to capture
                # later).
                pre_existing_hash = sha256_of_file(surface.path)
                choice = decide(PlanItem(path=surface.path))
                collision_decisions.append({
                    "item": rel_path,
                    "kind": "whole-file",
                    "choice": choice,
                    "existing_sha256": pre_existing_hash,
                    "decided_at": datetime.datetime.now(
                        datetime.UTC
                    ).isoformat(),
                })
            if choice == "overwrite":
                actions.append(
                    Action(kind="overwrite_with_backup", surface=surface)
                )
            # "keep-existing" -> no action, but the decision above is
            # still persisted so a later run doesn't re-ask.

    if errors:
        return Plan(ok=False, actions=[], errors=errors)
    return Plan(
        ok=True,
        actions=actions,
        errors=[],
        collision_decisions=collision_decisions,
    )


def journal_status(journal_path: Path) -> dict[str, Any]:
    journal_path = Path(journal_path)
    if not journal_path.exists():
        return {"pending": False, "summary": []}
    data: dict[str, Any] = json.loads(journal_path.read_text())
    return {"pending": True, "summary": data.get("plan_summary", [])}


def _write_journal(journal_path: Path, plan: Plan, base_dir: Path) -> None:
    summary = [
        f"{_rel(a.surface.path, base_dir)}: {a.kind}" for a in plan.actions
    ]
    journal_path.write_text(
        json.dumps({"plan_summary": summary}, indent=2) + "\n"
    )


def apply_plan(
    plan: Plan,
    state: dict[str, Any],
    base_dir: Path,
    journal_path: Path,
    install_id: str,
) -> dict[str, Any]:
    """Apply every action in a validated (plan.ok) plan, journaling
    before mutation. Returns the updated state dict — the caller is
    responsible for calling save_state() with it, and ONLY THEN
    deleting journal_path (this function deliberately does not delete
    it — see spec section 6's crash-consistency requirement: the
    journal must survive a crash between this returning and the
    caller's save_state() call, so a leftover journal always means
    "state may not reflect what's on disk," never "state is fine, some
    other unrelated file happened to still exist.")."""
    if not plan.ok:
        raise ValueError("cannot apply a plan with ok=False")

    _write_journal(Path(journal_path), plan, base_dir)

    for action in plan.actions:
        surface = action.surface
        rel_path = _rel(surface.path, base_dir)

        if action.kind == "upsert_block":
            # Captured BEFORE any write, and keyed on EXISTENCE rather than
            # emptiness. `existing == ""` cannot tell a missing file from a
            # 0-byte one the user touched as a placeholder — and treating
            # the latter as ours means uninstall deletes their file.
            path_existed = surface.path.exists()
            surface.path.parent.mkdir(parents=True, exist_ok=True)
            existing = surface.path.read_text() if path_existed else ""
            rendered = bi.upsert_block(
                existing,
                surface.block_id,
                surface.block_version,
                surface.block_body,
            )
            bi.atomic_write(surface.path, rendered)
            block_hash = bi.sha256_bytes(
                bi.render_block(
                    surface.block_id,
                    surface.block_version,
                    surface.block_body,
                ).encode()
            )
            # Whether WE brought this file into existence, captured from
            # `existing` above (read before the write). uninstall needs it
            # to tell "delete the file we created" from "strip our block
            # out of the user's file" — emptiness alone cannot, because a
            # user may legitimately have an empty placeholder.
            #
            # A prior recording wins: on update/re-install the file always
            # exists by then, so recomputing would silently flip a
            # harness-created file to "pre-existed" and strand it forever.
            prior = next(
                (b for b in state["managed_blocks"] if b["file"] == rel_path),
                None,
            )
            created_by_harness = (
                prior.get("created_by_harness")
                if prior and "created_by_harness" in prior
                else not path_existed
            )
            state["managed_blocks"] = [
                b for b in state["managed_blocks"] if b["file"] != rel_path
            ] + [{
                "file": rel_path,
                "block_id": surface.block_id,
                "rendered_version": surface.block_version,
                "rendered_sha256": block_hash,
                "created_by_harness": created_by_harness,
            }]

        elif action.kind == "create":
            surface.path.parent.mkdir(parents=True, exist_ok=True)
            bi.atomic_write(surface.path, surface.content)
            # Track created whole-file surfaces so doctor can detect drift and
            # uninstall can clean them up. Use same created_by_harness logic
            # as managed_blocks: check prior state first, fall back to whether
            # the file already existed at plan time (created_by_harness=True).
            prior = next(
                (f for f in state["overwritten_files"] if f["file"] == rel_path),
                None,
            )
            created_by_harness = (
                prior.get("created_by_harness")
                if prior and "created_by_harness" in prior
                else True  # CREATE action means we're creating it, so it's ours
            )
            written_hash = bi.sha256_bytes(surface.content.encode())
            entry = {
                "file": rel_path,
                "written_sha256": written_hash,
                "created_by_harness": created_by_harness,
            }
            if surface.client:
                entry["client"] = surface.client
            state["overwritten_files"] = [
                f for f in state["overwritten_files"] if f["file"] != rel_path
            ] + [entry]

        elif action.kind == "overwrite_with_backup":
            backup = resolve_backup_path(
                surface.path,
                state,
                install_id=install_id,
                base_dir=base_dir,
            )
            if not backup.exists():
                backup.write_bytes(surface.path.read_bytes())
            backup_hash = sha256_of_file(backup)
            bi.atomic_write(surface.path, surface.content)
            written_hash = bi.sha256_bytes(surface.content.encode())
            entry = {
                "file": rel_path,
                "backup": _rel(backup, base_dir),
                "written_sha256": written_hash,
                "backup_sha256": backup_hash,
            }
            if surface.client:
                entry["client"] = surface.client
            state["overwritten_files"] = [
                f for f in state["overwritten_files"] if f["file"] != rel_path
            ] + [entry]

    # Collision decisions (both "overwrite" and "keep-existing") were
    # already captured at plan time in plan.collision_decisions, using
    # the pre-existing file's hash — merge them in here rather than
    # recomputing anything from post-mutation state.
    for decision in plan.collision_decisions:
        item = decision["item"]
        state["collision_decisions"] = [
            d for d in state["collision_decisions"] if d["item"] != item
        ] + [decision]

    return state


def _load_surfaces_spec(spec_path: Path) -> list[Surface]:
    """spec_path is a JSON file harness-link.sh writes describing what to
    install: a list of {"path", "is_block_surface", "block_body" or
    "content", "block_id", "block_version"} objects. Keeping this as a
    file (not argv) avoids shell-escaping rendered markdown bodies."""
    raw = json.loads(Path(spec_path).read_text())
    return [
        Surface(
            path=Path(r["path"]),
            **{k: v for k, v in r.items() if k != "path"},
        )
        for r in raw
    ]


def _prune_empty_parents(start: Path, base_dir: Path) -> None:
    """Remove directories left empty by deleting a harness-created file.

    Deleting the only file the harness put in a directory it also created
    (.github/copilot-instructions.md being the common one) otherwise strands
    an empty .github/ in the consumer's tree.

    Uses rmdir, never a recursive delete: a directory holding anything at
    all — the operator's own workflows, an unrelated dotfile — raises
    OSError and stops the walk right there, so nothing they own is at risk.
    Stops at base_dir so uninstall can never climb out of the project.
    """
    current = start.resolve()
    root = base_dir.resolve()
    while current != root and root in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _restore_or_delete_entry(entry: dict[str, Any], base_dir: Path) -> tuple[str, bool]:
    """Apply the harness's one safety rule for reversing a single
    overwritten_files entry, shared by uninstall_all() (drops every
    entry regardless of outcome) and remove_clients() (must know
    whether cleanup actually happened, to decide whether to keep
    tracking an entry it left in place). Returns (log_line, cleaned_up):
    delete a harness-created file, or restore a pre-existing one from
    backup, only when on-disk content still matches written_sha256 —
    never touch a file a user has hand-edited since install."""
    path = base_dir / entry["file"]

    if entry.get("created_by_harness") is True:
        if not path.exists():
            return f"{entry['file']}: deleted since install, nothing to remove", True
        current_hash = sha256_of_file(path)
        if current_hash != entry["written_sha256"]:
            return (
                f"{entry['file']}: edited since install — left in place "
                "(we created it and can't safely restore to nothing)",
                False,
            )
        path.unlink(missing_ok=True)
        _prune_empty_parents(path.parent, base_dir)
        return (
            f"{entry['file']}: removed (we created it from nothing, "
            "and it matches what we wrote)",
            True,
        )

    backup = base_dir / entry["backup"]
    if not path.exists():
        return f"{entry['file']}: deleted since install, nothing to restore", True
    current_hash = sha256_of_file(path)
    if current_hash != entry["written_sha256"]:
        return (
            f"{entry['file']}: edited since install — left in place; "
            f"backup available at {entry['backup']}",
            False,
        )
    if not backup.exists():
        return (
            f"{entry['file']}: backup missing ({entry['backup']}) — left in place",
            False,
        )
    bi.atomic_write(path, backup.read_text())
    return f"{entry['file']}: restored from backup", True


def remove_clients(
    state: dict[str, Any], base_dir: Path, removed_clients: set[str]
) -> list[str]:
    """Reverse only the overwritten_files entries belonging to clients no
    longer selected (cmd_update's --client switch), using the exact same
    per-file safety rule as uninstall_all(): delete/restore only when
    on-disk content still matches what the harness wrote, never when a
    user has hand-edited the file since. An entry a rule leaves in place
    (drift or missing backup) stays tracked in overwritten_files rather
    than being silently dropped, so 'doctor'/a later run can still see
    and report it instead of the file going untracked with no trail."""
    log: list[str] = []
    remaining: list[dict[str, Any]] = []
    for entry in state.get("overwritten_files", []):
        if entry.get("client") in removed_clients:
            line, cleaned_up = _restore_or_delete_entry(entry, base_dir)
            log.append(line)
            if not cleaned_up:
                remaining.append(entry)
        else:
            remaining.append(entry)
    state["overwritten_files"] = remaining
    return log


# Client label inferred from the always-on managed_blocks paths -- these
# entries predate --client (P1-01) and were never given a 'client' field of
# their own, unlike overwritten_files (see cmd_generate_clients). The
# mapping mirrors generate-clients' own per-client target file names.
_MANAGED_BLOCK_CLIENT_BY_FILE = {
    "CLAUDE.md": "claude",
    "AGENTS.md": "codex",
    "GEMINI.md": "gemini",
    ".github/copilot-instructions.md": "copilot",
}


def client_surface_status(
    state: dict[str, Any], base_dir: Path
) -> list[dict[str, Any]]:
    """Drift status for every client-facing surface this install tracks --
    the always-on managed_blocks files and any --client-generated
    overwritten_files -- for 'audit --json' (P2-07). A new function rather
    than reusing 'doctor's inline check: doctor prints human-readable lines
    and exits non-zero on drift; audit needs structured per-file status
    with no side effect on exit code, and this is the one place both could
    share the comparison logic without duplicating it a second time."""
    results: list[dict[str, Any]] = []

    for entry in state.get("managed_blocks", []):
        file_rel = entry["file"]
        client = _MANAGED_BLOCK_CLIENT_BY_FILE.get(file_rel)
        path = base_dir / file_rel
        status = "ok"
        if not path.exists():
            status = "missing"
        else:
            try:
                content = path.read_text(encoding="utf-8")
                matches = bi.find_blocks(content, entry["block_id"])
            except (OSError, bi.MarkerError):
                status = "malformed"
            else:
                if len(matches) != 1:
                    status = "malformed"
                else:
                    m = matches[0]
                    current_hash = bi.sha256_bytes(
                        content[m.start : m.end].encode("utf-8")
                    )
                    rendered = entry.get("rendered_sha256")
                    status = "ok" if current_hash == rendered else "drift"
        results.append(
            {
                "file": file_rel,
                "client": client,
                "kind": "managed_block",
                "status": status,
            }
        )

    for entry in state.get("overwritten_files", []):
        file_rel = entry["file"]
        path = base_dir / file_rel
        status = "ok"
        if not path.exists():
            status = "missing"
        else:
            current_hash = sha256_of_file(path)
            status = "ok" if current_hash == entry.get("written_sha256") else "drift"
        results.append(
            {
                "file": file_rel,
                "client": entry.get("client"),
                "kind": "overwritten_file",
                "status": status,
            }
        )

    return results


def uninstall_all(state: dict[str, Any], base_dir: Path) -> list[str]:
    """Reverse every managed block and overwritten file recorded in
    state, per the spec's per-file-class uninstall semantics. Returns a
    list of human-readable log lines for harness-link.sh to print."""
    log: list[str] = []

    for entry in state.get("managed_blocks", []):
        path = base_dir / entry["file"]
        if not path.exists():
            log.append(f"{entry['file']}: no longer exists, nothing to remove")
            continue
        content = path.read_text()
        removed = bi.remove_block(content, entry["block_id"])
        if removed != content:
            # Delete only what we created AND that is now empty. Both
            # conditions are needed: emptiness alone would delete a user's
            # pre-existing empty placeholder, and provenance alone would
            # delete a file they had since put content into. Provenance
            # missing (state written before it was recorded) counts as
            # "not ours" — an old install must not become a delete on
            # upgrade.
            harness_made_it = entry.get("created_by_harness") is True
            if removed.strip() or not harness_made_it:
                bi.atomic_write(path, removed)
                log.append(f"{entry['file']}: removed managed block")
            else:
                # missing_ok: the file can vanish between the read above
                # and here (concurrent cleanup), and that must not strand
                # the entries still to process.
                path.unlink(missing_ok=True)
                _prune_empty_parents(path.parent, base_dir)
                log.append(
                    f"{entry['file']}: removed managed block and the file, "
                    "which we created and which held nothing else"
                )
        else:
            log.append(f"{entry['file']}: block not found, nothing to remove")

    # Harness-created whole-file surfaces (CREATE action) have no backup: we
    # created them from nothing, so uninstall deletes them (same logic as
    # managed_blocks with created_by_harness=True and empty content). Files
    # we overwrote (pre-existing) have a backup: restore from it. Both
    # follow the one safety rule in _restore_or_delete_entry(), shared with
    # remove_clients() — never touch a file the user has hand-edited since.
    for entry in state.get("overwritten_files", []):
        line, _ = _restore_or_delete_entry(entry, base_dir)
        log.append(line)

    state["managed_blocks"] = []
    state["overwritten_files"] = []
    return log


def classify_skill_updates(
    *,
    current: list[str],
    to_add: list[str],
    source_path: Path,
    target: Path,
    skill_sources: dict[str, str],
) -> dict[str, list[str]]:
    """For each copy-mode skill in `current` that isn't newly being
    added, decide whether its drift from upstream (if any) is safe to
    apply directly (upstream_changed -> to_refresh) or needs to
    preserve a consumer's local edit instead (local_edit -> to_backup).
    A skill with no recorded as-installed hash (predates skill_sources
    tracking) is treated as upstream_changed -- a conservative default
    that avoids false-positive backups for skills installed before this
    tracking existed; the next apply starts tracking its hash. Scoped to
    .claude/skills only -- the other skill destination mirrors
    (.agents/skills, .qwen/skills) are classified in lockstep with it
    rather than independently, since consumers interact with
    .claude/skills directly and the mirrors exist for other clients'
    on-demand discovery, not for hand-editing."""
    to_refresh: list[str] = []
    to_backup: list[str] = []
    for name in current:
        if name in to_add:
            continue
        source_dir = source_path / ".claude" / "skills" / name
        installed_dir = target / ".claude" / "skills" / name
        if not installed_dir.is_dir() or not source_dir.is_dir():
            continue
        installed_hash = hash_dir_tree(installed_dir)
        if hash_dir_tree(source_dir) == installed_hash:
            continue  # unchanged, nothing to do
        as_installed = skill_sources.get(name)
        if as_installed is None or as_installed == installed_hash:
            to_refresh.append(name)
        else:
            to_backup.append(name)
    return {"to_refresh": to_refresh, "to_backup": to_backup}


def apply_skill_sources(
    *,
    state: dict[str, Any],
    target: Path,
    current: list[str],
    to_remove: list[str],
    to_backup: list[str],
) -> None:
    """Update state["skill_sources"] in place after a copy-mode apply:
    drop entries for removed skills, preserve to_backup entries
    unchanged (their on-disk content still diverges from upstream on
    purpose -- a consumer's edit, backed up rather than overwritten, so
    the next update must keep recognizing the divergence), and
    recompute the hash for every other currently-selected skill from
    its now-on-disk content (which matches upstream, since it was just
    (re-)copied)."""
    sources: dict[str, str] = state.setdefault("skill_sources", {})
    for name in to_remove:
        sources.pop(name, None)
    for name in current:
        if name in to_backup:
            continue
        installed_dir = target / ".claude" / "skills" / name
        if installed_dir.is_dir():
            sources[name] = hash_dir_tree(installed_dir)


def _cli_classify_skill_updates(args: Any) -> None:
    state = load_state(Path(args.state))
    current = [s for s in args.current.split(",") if s]
    to_add = [s for s in args.to_add.split(",") if s] if args.to_add else []
    result = classify_skill_updates(
        current=current,
        to_add=to_add,
        source_path=Path(args.source_path),
        target=Path(args.target),
        skill_sources=state.get("skill_sources", {}),
    )
    print(json.dumps(result))


def _cli_apply_skill_sources(args: Any) -> None:
    state = load_state(Path(args.state))
    current = [s for s in args.current.split(",") if s]
    to_remove = [s for s in args.to_remove.split(",") if s] if args.to_remove else []
    to_backup = [s for s in args.to_backup.split(",") if s] if args.to_backup else []
    apply_skill_sources(
        state=state,
        target=Path(args.target),
        current=current,
        to_remove=to_remove,
        to_backup=to_backup,
    )
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True}))


def _cli_uninstall(args: Any) -> None:
    state = load_state(Path(args.state))
    log = uninstall_all(state, base_dir=Path(args.base_dir))
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "log": log}))


def _cli_remove_clients(args: Any) -> None:
    state = load_state(Path(args.state))
    removed = {c for c in args.clients.split(",") if c}
    log = remove_clients(state, Path(args.base_dir), removed)
    save_state(Path(args.state), state)
    print(json.dumps({"ok": True, "log": log}))


def _cli_journal_status(args: Any) -> None:
    print(json.dumps(journal_status(Path(args.journal))))


def _cli_plan(args: Any) -> None:
    surfaces = _load_surfaces_spec(args.surfaces)
    state = load_state(Path(args.state))
    base_dir = Path(args.base_dir)
    decisions: list[str] = []

    def decide(item: PlanItem) -> str:
        decisions.append(str(item.path))
        return "report-only"

    plan = build_plan(
        surfaces,
        state,
        install_id=args.install_id,
        base_dir=base_dir,
        decide=decide,
    )
    print(
        json.dumps({
            "ok": plan.ok,
            "errors": plan.errors,
            "actions": [
                {"kind": a.kind, "path": str(a.surface.path)}
                for a in plan.actions
            ],
            "collisions": decisions,
        })
    )


def _cli_apply(args: Any) -> None:
    surfaces = _load_surfaces_spec(args.surfaces)
    state = load_state(Path(args.state))
    base_dir = Path(args.base_dir)

    decisions_map: dict[str, str] = {}
    if args.decisions:
        decisions_map = json.loads(Path(args.decisions).read_text())

    def decide(item: PlanItem) -> str:
        return decisions_map.get(str(item.path), "keep-existing")

    plan = build_plan(
        surfaces,
        state,
        install_id=args.install_id,
        base_dir=base_dir,
        decide=decide,
    )
    if not plan.ok:
        print(json.dumps({"ok": False, "errors": plan.errors}))
        raise SystemExit(1)

    journal_path = Path(args.journal)
    updated_state = apply_plan(
        plan,
        state=state,
        base_dir=base_dir,
        journal_path=journal_path,
        install_id=args.install_id,
    )
    save_state(Path(args.state), updated_state)
    # Only delete the journal after state has actually been persisted —
    # if the process crashes between apply_plan() returning and this
    # line, the journal must still be here for 'doctor' to find.
    journal_path.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "applied": len(plan.actions)}))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="install_transaction.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_journal = sub.add_parser(
        "journal-status", help="Report a leftover crash journal, if any."
    )
    p_journal.add_argument("--journal", required=True)
    p_journal.set_defaults(func=_cli_journal_status)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--surfaces", required=True)
    p_plan.add_argument("--state", required=True)
    p_plan.add_argument("--base-dir", required=True)
    p_plan.add_argument("--install-id", required=True)
    p_plan.set_defaults(func=_cli_plan)

    p_apply = sub.add_parser("apply")
    p_apply.add_argument("--surfaces", required=True)
    p_apply.add_argument("--state", required=True)
    p_apply.add_argument("--base-dir", required=True)
    p_apply.add_argument("--install-id", required=True)
    p_apply.add_argument("--journal", required=True)
    p_apply.add_argument("--decisions", default=None)
    p_apply.set_defaults(func=_cli_apply)

    p_uninstall = sub.add_parser("uninstall")
    p_uninstall.add_argument("--state", required=True)
    p_uninstall.add_argument("--base-dir", required=True)
    p_uninstall.set_defaults(func=_cli_uninstall)

    p_remove_clients = sub.add_parser(
        "remove-clients",
        help="Reverse overwritten_files entries for clients no longer selected.",
    )
    p_remove_clients.add_argument("--state", required=True)
    p_remove_clients.add_argument("--base-dir", required=True)
    p_remove_clients.add_argument(
        "--clients", required=True, help="comma-separated client names to remove"
    )
    p_remove_clients.set_defaults(func=_cli_remove_clients)

    p_classify_skills = sub.add_parser(
        "classify-skill-updates",
        help="Split copy-mode skills with source/installed drift into "
        "upstream-changed (safe to refresh) vs. local-edit (needs backup).",
    )
    names_help = "comma-separated skill names"
    p_classify_skills.add_argument("--state", required=True)
    p_classify_skills.add_argument("--source-path", required=True)
    p_classify_skills.add_argument("--target", required=True)
    p_classify_skills.add_argument("--current", required=True, help=names_help)
    p_classify_skills.add_argument(
        "--to-add", default="", help=f"{names_help} (newly added, skipped)"
    )
    p_classify_skills.set_defaults(func=_cli_classify_skill_updates)

    p_apply_skill_sources = sub.add_parser(
        "apply-skill-sources",
        help="Recompute/prune state's skill_sources map after a copy-mode apply.",
    )
    p_apply_skill_sources.add_argument("--state", required=True)
    p_apply_skill_sources.add_argument("--target", required=True)
    p_apply_skill_sources.add_argument("--current", required=True, help=names_help)
    p_apply_skill_sources.add_argument("--to-remove", default="", help=names_help)
    p_apply_skill_sources.add_argument("--to-backup", default="", help=names_help)
    p_apply_skill_sources.set_defaults(func=_cli_apply_skill_sources)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
