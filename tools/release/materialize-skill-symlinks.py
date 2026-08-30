#!/usr/bin/env python3
"""npm prepack/postpack hook.

npm tarballs don't preserve symlinks (git does), and a few skills bundle
resources as relative symlinks back into patterns/ (e.g.
.claude/skills/agentic-loops/agent_loop.py -> ../../../patterns/
agentic-loops/agent_loop.py) rather than duplicating the file. Left
alone, `npm pack`/`npm publish` would silently drop those files from the
published tarball. 'materialize' replaces each such symlink with a real
copy of its target just before packing, recording each one's original
(unresolved) link target in a manifest; 'restore' puts the symlinks back
afterward from that manifest. Restoring from the manifest we wrote,
rather than `git checkout`, means this round-trips correctly even
outside a normal git work tree (a bare repo, or a source package with no
.git at all) instead of failing or silently leaving materialized files
in place.
"""
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
MANIFEST_PATH = REPO_ROOT / ".agentharness-materialize-manifest.json"


def materialize() -> None:
    manifest: dict[str, str] = {}
    for link in sorted(SKILLS_DIR.rglob("*")):
        if not link.is_symlink():
            continue
        target = link.resolve()
        # Every bundled-resource symlink this repo actually uses points
        # back into the repo itself (e.g. patterns/agentic-loops/). A
        # symlink resolving outside the repo root is either a mistake or
        # something worse — not a file `npm pack` should ever copy into
        # a published tarball — so refuse rather than blindly follow it.
        if not target.is_relative_to(REPO_ROOT):
            raise ValueError(
                f"{link} resolves outside the repo root ({target}) — refusing to materialize"
            )
        if not target.is_file():
            raise ValueError(f"{link} resolves to {target}, which isn't a regular file")
        # Record the raw (unresolved) link target before touching
        # anything, and persist after each entry — a crash partway
        # through a multi-symlink run still leaves a manifest that
        # accurately describes everything materialized so far.
        manifest[str(link.relative_to(REPO_ROOT))] = str(link.readlink())
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        # Copy before unlinking: if copy2() fails partway (disk full, a
        # permissions error), the symlink is still there to retry/restore
        # from, instead of leaving neither a symlink nor a real file.
        shutil.copy2(target, link.with_name(link.name + ".materializing"))
        link.unlink()
        link.with_name(link.name + ".materializing").rename(link)


def restore() -> None:
    """Restore symlinks from the manifest materialize() wrote.

    A missing manifest means there is nothing to restore (already
    restored, or materialize() was never run) -- not an error.
    """
    if not MANIFEST_PATH.exists():
        print(
            "materialize-skill-symlinks.py restore: no manifest at "
            f"{MANIFEST_PATH} -- nothing to restore.",
            file=sys.stderr,
        )
        return
    manifest: dict[str, str] = json.loads(MANIFEST_PATH.read_text())
    for rel_path, raw_target in manifest.items():
        link = REPO_ROOT / rel_path
        link.unlink()
        link.symlink_to(raw_target)
    MANIFEST_PATH.unlink()


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "materialize":
        materialize()
    elif action == "restore":
        restore()
    else:
        print(
            "usage: materialize-skill-symlinks.py {materialize|restore}",
            file=sys.stderr,
        )
        sys.exit(1)
