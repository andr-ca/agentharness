#!/usr/bin/env bats
# Tests for tools/release/materialize-skill-symlinks.py — the npm
# prepack/postpack hook that dereferences .claude/skills/ bundled-resource
# symlinks (npm tarballs don't preserve symlinks) and restores them
# afterward from a manifest materialize() writes (not `git checkout` —
# see the script's own module docstring for why).

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$REPO_ROOT/tools/release/materialize-skill-symlinks.py"
    MANIFEST="$REPO_ROOT/.agentharness-materialize-manifest.json"
}

teardown() {
    # Always leave the real repo's skill symlinks exactly as git tracks them,
    # even if a test fails partway through.
    if [ -f "$MANIFEST" ]; then
        python3 "$SCRIPT" restore >/dev/null 2>&1 || true
    fi
    git -C "$REPO_ROOT" checkout -- .claude/skills >/dev/null 2>&1 || true
    rm -f "$MANIFEST"
}

@test "materialize-skill-symlinks: agentic-loops bundled symlinks exist before the test" {
    [ -L "$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py" ]
}

@test "materialize-skill-symlinks: materialize replaces symlinks with real files of identical content" {
    local link="$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py"
    local expected
    expected="$(cat "$link")"

    python3 "$SCRIPT" materialize

    [ -f "$link" ]
    [ ! -L "$link" ]
    [ "$(cat "$link")" = "$expected" ]
    [ -f "$MANIFEST" ]
}

@test "materialize-skill-symlinks: restore puts the symlinks back from the manifest" {
    python3 "$SCRIPT" materialize
    [ ! -L "$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py" ]

    python3 "$SCRIPT" restore

    [ -L "$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py" ]
    [ ! -f "$MANIFEST" ]
    run git -C "$REPO_ROOT" status --short .claude/skills
    [ -z "$output" ]
}

@test "materialize-skill-symlinks: restore works with no git repo present at all" {
    local scratch
    scratch="$(mktemp -d)"
    # Deliberately just the one symlink under test, not a copy of the
    # whole agentic-loops dir -- other files there are symlinked at a
    # different relative depth (.claude/skills/agentic-loops/... in the
    # real repo) and would resolve outside $scratch if copied verbatim.
    mkdir -p "$scratch/agentic-loops" "$scratch/patterns/agentic-loops"
    cp "$REPO_ROOT/patterns/agentic-loops/agent_loop.py" "$scratch/patterns/agentic-loops/agent_loop.py"
    ln -sf ../patterns/agentic-loops/agent_loop.py "$scratch/agentic-loops/agent_loop.py"

    # No .git anywhere under $scratch -- confirms restore has no git dependency.
    [ ! -d "$scratch/.git" ]

    python3 - "$scratch" "$SCRIPT" <<'PYEOF'
import importlib.util
import sys
from pathlib import Path

scratch = Path(sys.argv[1]).resolve()
script_path = sys.argv[2]
spec = importlib.util.spec_from_file_location("mss", script_path)
mss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mss)
mss.REPO_ROOT = scratch
mss.SKILLS_DIR = scratch / "agentic-loops"
mss.MANIFEST_PATH = scratch / ".agentharness-materialize-manifest.json"

mss.materialize()
assert not (scratch / "agentic-loops" / "agent_loop.py").is_symlink()
mss.restore()
assert (scratch / "agentic-loops" / "agent_loop.py").is_symlink()
assert not mss.MANIFEST_PATH.exists()
PYEOF

    rm -rf "$scratch"
}

@test "materialize-skill-symlinks: materialize preserves manifest entries from a crashed prior run" {
    local link="$REPO_ROOT/.claude/skills/agentic-loops/agent_loop.py"
    local raw_target
    raw_target="$(python3 -c "from pathlib import Path; print(Path('$link').readlink())")"

    # Simulate a materialize() run that crashed after processing this one
    # symlink but before finishing any others: the file is already a real
    # file (not a symlink, so the loop won't rediscover it) and a manifest
    # already exists recording its original target.
    local content
    content="$(cat "$link")"
    rm "$link"
    printf '%s' "$content" > "$link"
    printf '{\n  "%s": "%s"\n}\n' ".claude/skills/agentic-loops/agent_loop.py" "$raw_target" > "$MANIFEST"

    python3 "$SCRIPT" materialize

    # The pre-existing entry must survive materialize()'s rewritten manifest.
    run python3 -c "import json; print(json.load(open('$MANIFEST'))['.claude/skills/agentic-loops/agent_loop.py'])"
    [ "$status" -eq 0 ]
    [ "$output" = "$raw_target" ]

    python3 "$SCRIPT" restore
    [ -L "$link" ]
    run git -C "$REPO_ROOT" status --short .claude/skills
    [ -z "$output" ]
}

@test "materialize-skill-symlinks: restore is a no-op when no manifest exists" {
    [ ! -f "$MANIFEST" ]
    run python3 "$SCRIPT" restore
    [ "$status" -eq 0 ]
    [[ "$output" == *"nothing to restore"* ]]
}

@test "materialize-skill-symlinks: rejects an unknown action" {
    run python3 "$SCRIPT" bogus
    [ "$status" -ne 0 ]
    [[ "$output" == *"usage:"* ]]
}
