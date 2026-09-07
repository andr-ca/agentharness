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
                f"{MAP_FILENAME} entry {i} must be a mapping with 'paths' "
                "and 'docs' keys"
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
