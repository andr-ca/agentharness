# Doc-Ownership Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a completion-gate check (`tools/verify-doc-ownership.py`) that fails when a branch touches a code path listed in `DOC_OWNERSHIP.yaml` without also touching the doc(s) that own it — unless the path is unmapped (in which case the fix is to add a map entry) or a `Docs-not-needed:` trailer is present on the branch.

**Architecture:** A standalone script, structured exactly like `tools/verify-content-quality.py` (module-level pure functions returning `list[str]` of error messages, a `main()` that prints and sets the exit code). It shells out to `git` for merge-base/diff/log, reads `DOC_OWNERSHIP.yaml` with PyYAML (already a dependency), and matches paths against globs with `fnmatch` (whose `*` already spans `/`, so no special `**` handling is needed). Wired into `tools/check-completion.sh` as a new gate, and into the repo's existing lint/type/test wiring for `tools/verify-content-quality.py` (ruff-legacy, mypy-legacy, `tools/check.sh`, CI's `content-quality` job) so the new script and its tests get the same coverage that script already has.

**Tech Stack:** Python 3 (stdlib `subprocess`, `fnmatch`, `pathlib`), PyYAML, pytest, `git`.

**Spec:** `docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md` — read it first; this plan implements sections 1–3 only. Section 4 (bootstrap question + `harness-link.sh --with-docs-check` flag) is deferred future work, not part of this plan.

**Scope note:** Every step below happens on branch `docs/doc-ownership-gate-design` (already checked out, lock already held under `AGENTHARNESS_AGENT_ID`). Do not create a new branch.

---

### Task 1: Ownership-map data model and loader

**Files:**
- Create: `tools/verify-doc-ownership.py`
- Create: `tools/tests/test_verify_doc_ownership.py`

- [x] **Step 1: Write the failing tests for `load_ownership_map`**

```python
"""Tests for tools/verify-doc-ownership.py."""
import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

MODULE_PATH = Path(__file__).resolve().parents[1] / "verify-doc-ownership.py"
spec = importlib.util.spec_from_file_location("verify_doc_ownership", MODULE_PATH)
vdo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdo)


def test_load_ownership_map_missing_file_returns_empty(tmp_path):
    assert vdo.load_ownership_map(tmp_path) == []


def test_load_ownership_map_parses_entries(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text(
        "- paths: [\"tools/setup/harness-link.sh\"]\n"
        "  docs: [\"docs/INTEGRATION.md\", \"MANIFEST.md\"]\n"
    )
    entries = vdo.load_ownership_map(tmp_path)
    assert entries == [
        vdo.OwnershipEntry(
            paths=("tools/setup/harness-link.sh",),
            docs=("docs/INTEGRATION.md", "MANIFEST.md"),
        )
    ]


def test_load_ownership_map_empty_file_returns_empty(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("")
    assert vdo.load_ownership_map(tmp_path) == []


def test_load_ownership_map_rejects_malformed_yaml(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("paths: [unterminated\n")
    with pytest.raises(vdo.MapError, match="not valid YAML"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_non_list_top_level(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("paths: [\"x\"]\n")
    with pytest.raises(vdo.MapError, match="must be a list"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_entry_missing_docs(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("- paths: [\"x\"]\n")
    with pytest.raises(vdo.MapError, match="entry 0"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_empty_docs_list(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text(
        "- paths: [\"x\"]\n  docs: []\n"
    )
    with pytest.raises(vdo.MapError, match="entry 0"):
        vdo.load_ownership_map(tmp_path)
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v`
Expected: `ModuleNotFoundError` / collection error, since `tools/verify-doc-ownership.py` does not exist yet (or `AttributeError` once the file exists but is empty — either way, FAIL).

- [x] **Step 3: Create `tools/verify-doc-ownership.py` with the map loader**

```python
#!/usr/bin/env python3
"""Doc-ownership gate (issue #320): fails if a branch touches a code path
listed in DOC_OWNERSHIP.yaml without also touching the doc(s) that own
it -- or, if the path isn't listed at all, without adding an entry for
it. A `Docs-not-needed: <reason>` trailer anywhere in the branch's
commits exempts every currently-unsatisfied *mapped* path (not unmapped
ones -- those must still get a map entry).

See docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md.
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

MAP_FILENAME = "DOC_OWNERSHIP.yaml"
SPEC_PATH = "docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md"
TRAILER_KEY = "Docs-not-needed"

# fnmatch's `*` already matches across `/`, so these don't need `**`.
AUTO_EXEMPT_GLOBS = (
    "tools/tests/*",
    "tests/*",
    "*.md",
    MAP_FILENAME,
)


class OwnershipEntry(NamedTuple):
    paths: tuple[str, ...]
    docs: tuple[str, ...]


class MapError(Exception):
    """DOC_OWNERSHIP.yaml is missing, malformed, or a git operation this
    gate depends on (merge-base resolution) failed. Callers treat this
    as a single reported error, not a crash -- see check_doc_ownership."""


def load_ownership_map(repo_root: Path) -> list[OwnershipEntry]:
    map_path = repo_root / MAP_FILENAME
    if not map_path.exists():
        return []
    try:
        raw = yaml.safe_load(map_path.read_text())
    except yaml.YAMLError as exc:
        raise MapError(f"{MAP_FILENAME} is not valid YAML: {exc}") from exc
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise MapError(
            f"{MAP_FILENAME} must be a list of entries, got {type(raw).__name__}"
        )
    entries: list[OwnershipEntry] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or "paths" not in item or "docs" not in item:
            raise MapError(
                f"{MAP_FILENAME} entry {i} must be a mapping with 'paths' and 'docs' keys"
            )
        paths = tuple(item["paths"])
        docs = tuple(item["docs"])
        if not paths or not docs:
            raise MapError(
                f"{MAP_FILENAME} entry {i} must have at least one path and one doc"
            )
        entries.append(OwnershipEntry(paths=paths, docs=docs))
    return entries


def main() -> int:  # placeholder, replaced in Task 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v`
Expected: 7 passed.

- [x] **Step 5: Commit**

```bash
git add tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py
git commit -m "feat(doc-ownership): add ownership-map loader"
```

---

### Task 2: Path matching (auto-exempt + entry lookup)

**Files:**
- Modify: `tools/verify-doc-ownership.py`
- Modify: `tools/tests/test_verify_doc_ownership.py`

- [x] **Step 1: Write the failing tests**

Append to `tools/tests/test_verify_doc_ownership.py`:

```python
@pytest.mark.parametrize(
    "path",
    [
        "tools/tests/harness-lifecycle.bats",
        "tools/tests/helpers/make-runtime-fixtures.py",
        "tests/unit/test_cli.py",
        "docs/INTEGRATION.md",
        "README.md",
        "DOC_OWNERSHIP.yaml",
    ],
)
def test_is_auto_exempt_true_for_test_and_doc_paths(path):
    assert vdo.is_auto_exempt(path) is True


@pytest.mark.parametrize(
    "path",
    ["tools/setup/harness-link.sh", "src/agentharness/cli.py"],
)
def test_is_auto_exempt_false_for_code_paths(path):
    assert vdo.is_auto_exempt(path) is False


def test_required_docs_for_unmapped_path_returns_none():
    entries = [vdo.OwnershipEntry(paths=("tools/setup/*.sh",), docs=("docs/INTEGRATION.md",))]
    assert vdo.required_docs_for("src/other.py", entries) is None


def test_required_docs_for_matches_glob():
    entries = [vdo.OwnershipEntry(paths=("tools/setup/*.sh",), docs=("docs/INTEGRATION.md",))]
    assert vdo.required_docs_for("tools/setup/harness-link.sh", entries) == {"docs/INTEGRATION.md"}


def test_required_docs_for_unions_multiple_matching_entries():
    entries = [
        vdo.OwnershipEntry(paths=("tools/setup/*.sh",), docs=("docs/INTEGRATION.md",)),
        vdo.OwnershipEntry(paths=("tools/setup/harness-link.sh",), docs=("MANIFEST.md",)),
    ]
    result = vdo.required_docs_for("tools/setup/harness-link.sh", entries)
    assert result == {"docs/INTEGRATION.md", "MANIFEST.md"}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v -k "auto_exempt or required_docs"`
Expected: `AttributeError: module 'verify_doc_ownership' has no attribute 'is_auto_exempt'` (and similarly for `required_docs_for`).

- [x] **Step 3: Add the matching functions**

Insert into `tools/verify-doc-ownership.py`, after `load_ownership_map`:

```python
def is_auto_exempt(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in AUTO_EXEMPT_GLOBS)


def required_docs_for(path: str, entries: list[OwnershipEntry]) -> set[str] | None:
    """Union of `docs` across every entry whose `paths` matches. None
    means no entry matched at all (an unmapped path) -- distinct from a
    matched entry, which always has at least one doc by construction."""
    matched: set[str] | None = None
    for entry in entries:
        if any(fnmatch.fnmatch(path, pattern) for pattern in entry.paths):
            matched = (matched or set()) | set(entry.docs)
    return matched
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v`
Expected: all passing (12 total so far).

- [x] **Step 5: Commit**

```bash
git add tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py
git commit -m "feat(doc-ownership): add path matching and auto-exempt globs"
```

---

### Task 3: Git helpers (merge-base, changed files, escape-hatch trailer)

**Files:**
- Modify: `tools/verify-doc-ownership.py`
- Modify: `tools/tests/test_verify_doc_ownership.py`

These need a real git repo to run `git` against. Add a fixture helper that builds one deterministically, without a real network remote: it fakes `origin/main` with `git update-ref`, so `git merge-base origin/main HEAD` resolves the same way it would against a real fetched remote.

- [x] **Step 1: Write the failing tests**

Append to `tools/tests/test_verify_doc_ownership.py`:

```python
def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout


def _init_repo_with_fake_origin_main(tmp_path: Path) -> Path:
    """A repo with a `main` branch (commit A), a fake `origin/main` ref
    pointing at the same commit (no real remote needed), and a checked-out
    `feature` branch ready for the test to add commits to."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("# fixture\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-q", "-m", "initial")
    main_sha = _run_git(repo, "rev-parse", "HEAD").strip()
    _run_git(repo, "update-ref", "refs/remotes/origin/main", main_sha)
    _run_git(repo, "checkout", "-q", "-b", "feature")
    return repo


def _commit_all(repo: Path, message: str, trailer: str | None = None) -> None:
    _run_git(repo, "add", "-A")
    msg = message if trailer is None else f"{message}\n\n{trailer}"
    _run_git(repo, "commit", "-q", "-m", msg)


def test_resolve_merge_base_finds_common_ancestor(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add src.py")
    merge_base = vdo.resolve_merge_base(repo)
    assert merge_base == _run_git(repo, "rev-parse", "main").strip()


def test_resolve_merge_base_raises_when_ref_missing(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("# fixture\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-q", "-m", "initial")
    with pytest.raises(vdo.MapError, match="merge-base"):
        vdo.resolve_merge_base(repo)


def test_changed_files_lists_paths_since_merge_base(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "add src and docs")
    merge_base = vdo.resolve_merge_base(repo)
    assert set(vdo.changed_files(repo, merge_base)) == {"src.py", "docs.md"}


def test_has_docs_not_needed_trailer_false_by_default(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add src.py")
    merge_base = vdo.resolve_merge_base(repo)
    assert vdo.has_docs_not_needed_trailer(repo, merge_base) is False


def test_has_docs_not_needed_trailer_true_when_present(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "tweak timing", trailer="Docs-not-needed: internal only")
    merge_base = vdo.resolve_merge_base(repo)
    assert vdo.has_docs_not_needed_trailer(repo, merge_base) is True
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v -k "merge_base or changed_files or trailer"`
Expected: `AttributeError` — `resolve_merge_base`, `changed_files`, `has_docs_not_needed_trailer` don't exist yet.

- [x] **Step 3: Add the git helper functions**

Insert into `tools/verify-doc-ownership.py`, after `required_docs_for`:

```python
def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def resolve_merge_base(repo_root: Path, base_ref: str = "origin/main") -> str:
    try:
        return _git(repo_root, "merge-base", base_ref, "HEAD").strip()
    except RuntimeError as exc:
        raise MapError(
            f"could not resolve merge-base with {base_ref}: {exc}. "
            "This check needs a clone with an origin/main ref -- "
            "run 'git fetch origin main' first if this is a shallow clone."
        ) from exc


def changed_files(repo_root: Path, merge_base: str) -> list[str]:
    output = _git(repo_root, "diff", "--name-only", f"{merge_base}..HEAD")
    return [line for line in output.splitlines() if line]


def has_docs_not_needed_trailer(repo_root: Path, merge_base: str) -> bool:
    output = _git(repo_root, "log", f"{merge_base}..HEAD", "--pretty=%B")
    prefix = f"{TRAILER_KEY.lower()}:"
    return any(line.strip().lower().startswith(prefix) for line in output.splitlines())
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v`
Expected: all passing (17 total so far).

- [x] **Step 5: Commit**

```bash
git add tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py
git commit -m "feat(doc-ownership): add merge-base, diff, and trailer git helpers"
```

---

### Task 4: Orchestration and CLI entry point

**Files:**
- Modify: `tools/verify-doc-ownership.py`
- Modify: `tools/tests/test_verify_doc_ownership.py`

- [x] **Step 1: Write the failing tests**

Append to `tools/tests/test_verify_doc_ownership.py`:

```python
def _write_map(repo: Path, entries_yaml: str) -> None:
    (repo / "DOC_OWNERSHIP.yaml").write_text(entries_yaml)


def test_check_doc_ownership_passes_when_doc_touched(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "- paths: [\"src.py\"]\n  docs: [\"docs.md\"]\n")
    _commit_all(repo, "seed map")
    (repo / "src.py").write_text("x = 1\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "change src and doc together")
    assert vdo.check_doc_ownership(repo) == []


def test_check_doc_ownership_fails_when_doc_not_touched(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "- paths: [\"src.py\"]\n  docs: [\"docs.md\"]\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "seed map and doc")
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "change src only")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "src.py" in errors[0]
    assert "docs.md" in errors[0]


def test_check_doc_ownership_fails_on_unmapped_path(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add unmapped src.py")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "src.py" in errors[0]
    assert "no DOC_OWNERSHIP.yaml entry" in errors[0]


def test_check_doc_ownership_trailer_exempts_unsatisfied_mapped_path(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "- paths: [\"src.py\"]\n  docs: [\"docs.md\"]\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "seed map and doc")
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "tweak", trailer="Docs-not-needed: no behavior change")
    assert vdo.check_doc_ownership(repo) == []


def test_check_doc_ownership_trailer_does_not_exempt_unmapped_path(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add unmapped", trailer="Docs-not-needed: not relevant here")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "no DOC_OWNERSHIP.yaml entry" in errors[0]


def test_check_doc_ownership_ignores_auto_exempt_paths(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "tools" / "tests").mkdir(parents=True)
    (repo / "tools" / "tests" / "fixture.bats").write_text("# test\n")
    _commit_all(repo, "add test-only fixture")
    assert vdo.check_doc_ownership(repo) == []


def test_check_doc_ownership_reports_malformed_map_as_single_error(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "not: [a, list\n")
    _commit_all(repo, "add broken map")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "not valid YAML" in errors[0]


def test_main_returns_zero_on_clean_repo(tmp_path, monkeypatch, capsys):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "README.md").write_text("# fixture\nchanged\n")
    _commit_all(repo, "doc-only change")
    monkeypatch.chdir(repo)
    assert vdo.main() == 0
    assert "passed" in capsys.readouterr().out


def test_main_returns_one_and_prints_errors(tmp_path, monkeypatch, capsys):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add unmapped src.py")
    monkeypatch.chdir(repo)
    assert vdo.main() == 1
    out = capsys.readouterr().out
    assert "src.py" in out
    assert "1 issue(s) found" in out
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v -k "check_doc_ownership or main_returns"`
Expected: `AttributeError: ... has no attribute 'check_doc_ownership'`.

- [x] **Step 3: Replace the placeholder `main()` with the real orchestration**

In `tools/verify-doc-ownership.py`, replace the `def main() -> int: ...` placeholder from Task 1 with:

```python
def check_doc_ownership(repo_root: Path, base_ref: str = "origin/main") -> list[str]:
    try:
        entries = load_ownership_map(repo_root)
    except MapError as exc:
        return [str(exc)]

    try:
        merge_base = resolve_merge_base(repo_root, base_ref)
    except MapError as exc:
        return [str(exc)]

    all_changed = changed_files(repo_root, merge_base)
    changed_set = set(all_changed)

    errors: list[str] = []
    unsatisfied: list[tuple[str, set[str]]] = []
    for path in all_changed:
        if is_auto_exempt(path):
            continue
        required = required_docs_for(path, entries)
        if required is None:
            errors.append(
                f"{path}: no {MAP_FILENAME} entry -- add one before this can pass "
                f"(see {SPEC_PATH})"
            )
            continue
        if required & changed_set:
            continue
        unsatisfied.append((path, required))

    if unsatisfied and not has_docs_not_needed_trailer(repo_root, merge_base):
        for path, required in unsatisfied:
            errors.append(
                f"{path}: mapped to {sorted(required)}, but none were touched in "
                f"this branch -- update one of them, or add a "
                f"'{TRAILER_KEY}: <reason>' trailer to a commit"
            )

    return errors


def main() -> int:
    repo_root = Path.cwd()
    errors = check_doc_ownership(repo_root)
    if errors:
        print("Doc-ownership check failed:\n")
        for err in errors:
            print(f"  ✗ {err}")
        print(f"\n{len(errors)} issue(s) found.")
        return 1
    print("Doc-ownership check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Remove the old placeholder `main()`/`if __name__ == "__main__":` block from Task 1 (this replaces it).

- [x] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v`
Expected: all passing (26 total).

- [x] **Step 5: Commit**

```bash
git add tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py
git commit -m "feat(doc-ownership): add check orchestration and CLI entry point"
```

---

### Task 5: Wire into the completion gate, lint/type/test targets, and CI

**Files:**
- Modify: `tools/check-completion.sh`
- Modify: `tools/check.sh`
- Modify: `.github/workflows/ci.yml`

This mirrors exactly how `tools/verify-content-quality.py` and its test file are wired in each of these three places today.

- [ ] **Step 1: Add the enforcement gate to `tools/check-completion.sh`**

Insert a new gate between the existing "Gate 6: Packaged runtime matches source" block and "Gate 7: Git status" (find the `run_gate "runtime-artifact"` block ending around line 269, insert right after its closing `fi`):

```bash
# ---------------------------------------------------------------------------
# Gate 6b: Doc ownership -- a mapped code path must bring its doc along
# ---------------------------------------------------------------------------
run_gate "doc-ownership" python3 tools/verify-doc-ownership.py
```

- [ ] **Step 2: Add the new files to `ruff-legacy`/`mypy-legacy` in `tools/check-completion.sh`**

In the `legacy_targets` loop (the one containing `tools/verify-content-quality.py` and `tools/tests/test_verify_content_quality.py`), add two lines right after the existing `tools/tests/test_verify_content_quality.py` line:

```bash
        tools/verify-content-quality.py \
        tools/tests/test_verify_content_quality.py \
        tools/verify-doc-ownership.py \
        tools/tests/test_verify_doc_ownership.py \
        tools/generate-manifest.py \
```

Do the same in the `legacy_mypy` loop (mypy doesn't type-check test files by convention here — confirm by checking whether `tools/tests/test_verify_content_quality.py` appears in `legacy_mypy`; it does not in the current file, so only add `tools/verify-doc-ownership.py`, not the test file):

```bash
        tools/verify-content-quality.py \
        tools/verify-doc-ownership.py \
        tools/generate-manifest.py \
```

- [ ] **Step 3: Mirror the same two additions in `tools/check.sh`**

In the `step "ruff: legacy surfaces"` block, add after the `tools/verify-content-quality.py tools/tests/test_verify_content_quality.py \` line:

```bash
    tools/verify-content-quality.py tools/tests/test_verify_content_quality.py \
    tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py \
    tools/generate-manifest.py tools/release/materialize-skill-symlinks.py
```

In the `step "mypy: legacy surfaces"` block, add `tools/verify-doc-ownership.py` alongside `tools/verify-content-quality.py` (test file excluded, matching the existing pattern).

Add a new step for the script's own tests, right after the existing `step "pytest: duplicate-policy detection (tools/tests/test_verify_content_quality.py)"` block:

```bash
step "pytest: doc-ownership gate (tools/tests/test_verify_doc_ownership.py)"
python3 -m pytest tools/tests/test_verify_doc_ownership.py -q
```

- [ ] **Step 4: Mirror the same three additions in `.github/workflows/ci.yml`**

Line ~260 (`Ruff (isolated legacy surfaces)`): add `tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py` to the space-separated file list, in the same position as `tools/check.sh`'s equivalent line.

Line ~264 (`mypy (legacy surfaces)`): add `tools/verify-doc-ownership.py` to the list.

After line ~292 (`run: pytest tools/tests/test_verify_content_quality.py -v`), add a new step:

```yaml
      - name: Run doc-ownership gate tests
        run: pytest tools/tests/test_verify_doc_ownership.py -v
```

- [ ] **Step 5: Run the full local verification for this task**

Run: `ruff check --isolated tools/verify-doc-ownership.py tools/tests/test_verify_doc_ownership.py`
Expected: no output (clean).

Run: `mypy --config-file=/dev/null --no-error-summary tools/verify-doc-ownership.py`
Expected: no output (clean). If mypy complains about missing type stubs for `yaml`, check how `tools/verify-content-quality.py` handles this (it already imports `yaml` under the same `mypy --config-file=/dev/null` legacy configuration) — match whatever it does rather than adding a new suppression mechanism.

Run: `python3 -m pytest tools/tests/test_verify_doc_ownership.py -v`
Expected: all passing.

- [ ] **Step 6: Commit**

```bash
git add tools/check-completion.sh tools/check.sh .github/workflows/ci.yml
git commit -m "feat(doc-ownership): wire gate into completion gate, check.sh, and CI"
```

---

### Task 6: Seed the initial map and document the gate

This is the bootstrapping step: once Task 5's gate is live, *this branch's own diff* is subject to it. `tools/verify-doc-ownership.py` and `tools/check-completion.sh` are new/changed code paths with no map entry yet — `DOC_OWNERSHIP.yaml` doesn't exist before this task, so an entry must be added for them in this same task, in this same branch, or the gate fails against its own introduction.

**Files:**
- Create: `DOC_OWNERSHIP.yaml`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create the initial `DOC_OWNERSHIP.yaml`**

```yaml
# Doc-ownership map (issue #320): a PR touching a listed path must also
# touch one of its listed docs, or add a Docs-not-needed trailer. An
# unmapped path fails the gate outright -- add an entry for it here.
# See docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md.

- paths:
    - "tools/verify-doc-ownership.py"
    - "tools/check-completion.sh"
  docs:
    - "CLAUDE.md"
```

- [ ] **Step 2: Document the gate in `CLAUDE.md`'s Completion Gate table**

Find the "📋 Completion Gate" section's table (the one listing `content-quality`, `ruff-lint`, `mypy`, `pytest-coverage`, `shellcheck`, `git-clean`). Add a row:

```markdown
| `doc-ownership` | A changed path listed in `DOC_OWNERSHIP.yaml` must bring one of its owning docs along (or a `Docs-not-needed:` trailer) |
```

Immediately below the table (or in a short new subsection), add:

```markdown
**Doc-ownership map.** `DOC_OWNERSHIP.yaml` at the repo root lists code
paths and the doc(s) that own them. Touching a mapped path without
touching one of its docs fails the `doc-ownership` gate unless a commit
in the branch carries a `Docs-not-needed: <reason>` trailer. Touching a
path with **no** map entry at all also fails -- add an entry for it in
the same branch rather than skipping past it. See
`docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md` for the
full design and `tools/verify-doc-ownership.py` for the implementation.
```

- [ ] **Step 3: Verify the gate now passes against this branch's own diff**

Run: `python3 tools/verify-doc-ownership.py`
Expected: `Doc-ownership check passed.`, exit 0. (This works from a plain script invocation as long as `origin/main` is a valid ref in this checkout — it already is, since earlier steps in this session fetched/pulled `origin/main`.)

If it instead reports `tools/tests/test_verify_doc_ownership.py`, `tools/check.sh`, or `.github/workflows/ci.yml` as unmapped: those are auto-exempt (`tools/tests/*`) or need their own entry. `tools/check.sh` and `ci.yml` changes in Task 5 are process/wiring changes to files that are not themselves documented by a specific owning doc in this repo's existing doc set — if the gate flags them, add a second entry mapping them to `CLAUDE.md` as well (it already documents the completion-gate/CI relationship), rather than leaving the gate unsatisfied.

- [ ] **Step 4: Commit**

```bash
git add DOC_OWNERSHIP.yaml CLAUDE.md
git commit -m "feat(doc-ownership): seed initial map and document the gate in CLAUDE.md"
```

---

### Task 7: Full verification and push

**Files:** none (verification only)

- [ ] **Step 1: Run the full completion gate**

Run: `bash tools/check-completion.sh`
Expected: `"can_declare_complete":true` in the JSON output on stdout, and `PASS: doc-ownership` (among all the other gates) on stderr.

If `git-clean` fails because `DOC_OWNERSHIP.yaml` was just added in Task 6 but the file-placement guard (`.agentharness-guarded-paths.json` covers root-level new items) blocks it: this is a **new root-level file**, same class of guard hit earlier in this session for the spec doc. Ask the user for explicit permission, then record `DOC_OWNERSHIP.yaml` in `.agentharness-allowed-additions.txt` before re-committing, exactly as done for `docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md` earlier in this session.

- [ ] **Step 2: Run the full local check script**

Run: `bash tools/check.sh`
Expected: every step passes, including the new `pytest: doc-ownership gate` step.

- [ ] **Step 3: Push and open the PR**

Follow this repo's `committing` skill: publish authority is already granted (`.agentharness-publish-mode` exists), so push and open a PR referencing issue #320.

```bash
git push -u origin docs/doc-ownership-gate-design
gh pr create --title "feat(doc-ownership): require mapped code changes to touch their owning doc" \
  --body "Implements docs/superpowers/specs/2026-09-06-doc-ownership-gate-design.md sections 1-3. Closes #320 (sections 1-3; consumer bootstrap/flag rollout in section 4 is deferred future work, not closed by this PR)."
```

- [ ] **Step 4: Watch CI to a green terminal state**

Per this repo's mandate: don't report the push as done while CI is still running. Poll `gh pr checks <n> --watch` (or an equivalent loop) until every check reaches `pass`/`fail`, and read logs on any failure before deciding next steps.

---

## Out of scope for this plan

- Section 4 of the spec (bootstrap `docs.ownership` question, `harness-link.sh --with-docs-check` flag, `.agentharness-bin/check` wrapper wiring for consumers) — explicitly deferred in the spec until sections 1-3 are proven here. Track as a follow-up issue once this PR merges and has run for a while.
