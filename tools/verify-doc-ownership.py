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
    """Load and validate DOC_OWNERSHIP.yaml from repo_root.

    Returns an empty list if the file doesn't exist or is empty.
    Raises MapError if the file is malformed or an entry is invalid.
    """
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
                f"{MAP_FILENAME} entry {i} must be a mapping with 'paths' "
                "and 'docs' keys"
            )
        paths_val = item["paths"]
        docs_val = item["docs"]
        if not isinstance(paths_val, list):
            raise MapError(
                f"{MAP_FILENAME} entry {i}: 'paths' must be a list"
            )
        if not isinstance(docs_val, list):
            raise MapError(
                f"{MAP_FILENAME} entry {i}: 'docs' must be a list"
            )
        paths = tuple(paths_val)
        docs = tuple(docs_val)
        if not paths or not docs:
            raise MapError(
                f"{MAP_FILENAME} entry {i} must have at least one path and one doc"
            )
        entries.append(OwnershipEntry(paths=paths, docs=docs))
    return entries


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
