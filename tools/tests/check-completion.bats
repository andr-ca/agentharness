#!/usr/bin/env bats
# Tests for tools/check-completion.sh — the agent completion gate.
#
# Uses minimal stub projects to avoid running the full 70s pytest suite.

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$REPO_ROOT/tools/check-completion.sh"
}

_make_minimal_project() {
    # Create a minimal committed git project with stubs that pass ruff.
    # Uses a two-line verify-content-quality stub to avoid E702 (multiple
    # statements on one line). No src/, tests/, or pyproject.toml.
    local dir
    dir="$(mktemp -d)"
    git -C "$dir" init -q
    git -C "$dir" config user.email "test@example.com"
    git -C "$dir" config user.name "Test"
    mkdir -p "$dir/tools"
    cp "$SCRIPT" "$dir/tools/check-completion.sh"
    printf 'import sys\nsys.exit(0)\n' > "$dir/tools/verify-content-quality.py"
    git -C "$dir" add .
    git -C "$dir" commit -m "initial" -q
    echo "$dir"
}

@test "check-completion: stdout is valid JSON" {
    proj="$(_make_minimal_project)"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 -c "import json; json.loads('$output')"
}

@test "check-completion: JSON has required keys" {
    proj="$(_make_minimal_project)"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
assert "can_declare_complete" in d
assert "gates_passed" in d
assert "gates_failed" in d
assert isinstance(d["can_declare_complete"], bool)
PYEOF
}

@test "check-completion: stdout is a single JSON line" {
    proj="$(_make_minimal_project)"
    lines=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null | wc -l || true)
    rm -rf "$proj"
    [ "$lines" -eq 1 ]
}

@test "check-completion: exits 0 on clean project" {
    proj="$(_make_minimal_project)"
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 0 ]
}

@test "check-completion: exits 1 when a gate fails" {
    proj="$(_make_minimal_project)"
    # Override stub to fail
    printf 'import sys\nsys.exit(1)\n' > "$proj/tools/verify-content-quality.py"
    git -C "$proj" add . && git -C "$proj" commit -m "break" -q
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 1 ]
}

@test "check-completion: failing gate in gates_failed JSON" {
    proj="$(_make_minimal_project)"
    printf 'import sys\nsys.exit(1)\n' > "$proj/tools/verify-content-quality.py"
    git -C "$proj" add . && git -C "$proj" commit -m "break" -q
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
assert d["can_declare_complete"] is False
assert any("content-quality" in f for f in d["gates_failed"]), d
PYEOF
}

@test "check-completion: unborn HEAD handled gracefully" {
    fresh="$(mktemp -d)"
    git -C "$fresh" init -q
    mkdir -p "$fresh/tools"
    cp "$SCRIPT" "$fresh/tools/check-completion.sh"
    printf 'import sys\nsys.exit(0)\n' > "$fresh/tools/verify-content-quality.py"
    run bash -c "cd '$fresh' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$fresh"
    [ "$status" -le 1 ]
}

@test "check-completion: missing shellcheck in gates_failed" {
    proj="$(_make_minimal_project)"
    stripped=""
    IFS=':' read -ra entries <<< "$PATH"
    for e in "${entries[@]}"; do
        [ -x "$e/shellcheck" ] && continue
        stripped="${stripped:+$stripped:}$e"
    done
    output=$(cd "$proj" && env PATH="$stripped" bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
assert any("shellcheck" in f for f in d.get("gates_failed", [])), d
PYEOF
}

# ---------------------------------------------------------------------------
# JS/TS gate
# ---------------------------------------------------------------------------

@test "check-completion: JS project with passing lint script passes" {
    command -v node >/dev/null 2>&1 || skip "node not installed"
    command -v npm  >/dev/null 2>&1 || skip "npm not installed"
    proj="$(_make_minimal_project)"
    # Add a package.json with a lint script that exits 0
    cat > "$proj/package.json" << 'EOF'
{
  "name": "test",
  "version": "1.0.0",
  "scripts": { "lint": "node -e 'process.exit(0)'" }
}
EOF
    git -C "$proj" add . && git -C "$proj" commit -m "add pkg" -q
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 0 ]
}

@test "check-completion: JS project with failing lint script fails the gate" {
    command -v node >/dev/null 2>&1 || skip "node not installed"
    command -v npm  >/dev/null 2>&1 || skip "npm not installed"
    proj="$(_make_minimal_project)"
    cat > "$proj/package.json" << 'EOF'
{
  "name": "test",
  "version": "1.0.0",
  "scripts": { "lint": "node -e 'process.exit(1)'" }
}
EOF
    git -C "$proj" add . && git -C "$proj" commit -m "add pkg" -q
    run bash -c "cd '$proj' && bash tools/check-completion.sh 2>/dev/null"
    rm -rf "$proj"
    [ "$status" -eq 1 ]
}

@test "check-completion: project without package.json skips JS gate" {
    command -v node >/dev/null 2>&1 || skip "node not installed; test not applicable"
    # Verify that the JS gate doesn't run in a Python-only project
    proj="$(_make_minimal_project)"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads("""$output""")
# No JS gates should appear in passed or failed
js_gates = [g for g in d["gates_passed"] + d["gates_failed"]
            if "tsc" in g or "npm-lint" in g]
assert len(js_gates) == 0, f"Unexpected JS gates: {js_gates}"
PYEOF
}

# ---------------------------------------------------------------------------
# The gate's whole job is to be the last word before declaring work done, and
# new files are the one class of mistake it structurally could not see: a
# never-`git add`-ed file is not a tracked file, so `git diff HEAD` misses it
# while every other gate passes against the working tree that contains it.
# Observed live — a required skill symlink stayed untracked and the gate still
# reported can_declare_complete: true.
# ---------------------------------------------------------------------------

@test "check-completion: an untracked file fails git-clean" {
    proj="$(_make_minimal_project)"
    printf 'print("new")\n' > "$proj/brand_new_file.py"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json, sys
d = json.loads('''$output''')
assert d["can_declare_complete"] is False, d
assert any("git-clean" in g for g in d["gates_failed"]), d
PYEOF
}

@test "check-completion: a gitignored file does not fail git-clean" {
    # Genuinely transient output belongs in .gitignore, and the check must
    # respect that or it becomes noise everyone learns to ignore.
    proj="$(_make_minimal_project)"
    printf 'scratch/\n' > "$proj/.gitignore"
    git -C "$proj" add .gitignore
    git -C "$proj" -c user.email=t@e.com -c user.name=t commit -q -m gitignore
    mkdir -p "$proj/scratch" && printf 'junk\n' > "$proj/scratch/out.txt"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads('''$output''')
assert not any("git-clean" in g for g in d["gates_failed"]), d
PYEOF
}

@test "check-completion: a modified tracked file still fails git-clean" {
    proj="$(_make_minimal_project)"
    printf 'import sys\nsys.exit(1)\n' > "$proj/tools/verify-content-quality.py"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads('''$output''')
assert any("git-clean" in g for g in d["gates_failed"]), d
PYEOF
}

@test "check-completion: an unborn-HEAD repo with untracked files fails git-clean" {
    # The previous `rev-parse --verify HEAD` guard reported a repo with no
    # commits as clean regardless of its contents — the same blind spot as
    # untracked files, in a different disguise. `git status --porcelain`
    # works fine without any commits, so no guard is needed.
    dir="$(mktemp -d)"
    git -C "$dir" init -q
    mkdir -p "$dir/tools"
    cp "$SCRIPT" "$dir/tools/check-completion.sh"
    printf 'import sys\nsys.exit(0)\n' > "$dir/tools/verify-content-quality.py"
    output=$(cd "$dir" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$dir"
    python3 - <<PYEOF
import json
d = json.loads('''$output''')
assert any("git-clean" in g for g in d["gates_failed"]), d
PYEOF
}

@test "check-completion: an untracked directory is detected without enumerating it" {
    # --untracked-files=normal collapses it to one entry; detection must
    # still fire, which is the property that matters.
    proj="$(_make_minimal_project)"
    mkdir -p "$proj/build/deep" && touch "$proj/build/deep/a.o" "$proj/build/deep/b.o"
    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"
    python3 - <<PYEOF
import json
d = json.loads('''$output''')
failed = [g for g in d["gates_failed"] if "git-clean" in g]
assert failed, d
# One entry for the directory, not one per file inside it.
assert "1 uncommitted" in failed[0], failed
PYEOF
}

# ---------------------------------------------------------------------------
# The shellcheck gate must see COMMITTED changes.
#
# It compared only the working tree and the index, so a .sh file already
# committed was invisible — and the workflow this gate serves commits
# before running it, so on the mandated path shellcheck ran on nothing.
# A clean tree containing a demonstrably broken committed script reported
# "shellcheck (no .sh files changed)" and can_declare_complete: true.
# ---------------------------------------------------------------------------

_make_branch_project() {
    # A project with a real main branch and a feature branch, so the gate
    # has a merge-base to compare against — the situation every branch
    # this gate runs on is actually in.
    local dir
    dir="$(mktemp -d)"
    git -C "$dir" init -q -b main
    git -C "$dir" config user.email "test@example.com"
    git -C "$dir" config user.name "Test"
    mkdir -p "$dir/tools"
    cp "$SCRIPT" "$dir/tools/check-completion.sh"
    printf 'import sys\nsys.exit(0)\n' > "$dir/tools/verify-content-quality.py"
    git -C "$dir" add .
    git -C "$dir" commit -q -m "initial"
    git -C "$dir" checkout -q -b feature
    echo "$dir"
}

_stub_shellcheck() {
    # A stub that always reports problems, so the assertion is about
    # WHETHER shellcheck was consulted, not about any real finding.
    local dir="$1"
    mkdir -p "$dir/stubbin"
    printf '#!/usr/bin/env bash\nexit 1\n' > "$dir/stubbin/shellcheck"
    chmod +x "$dir/stubbin/shellcheck"
}

@test "check-completion: shellcheck runs on a .sh committed on this branch" {
    proj="$(_make_branch_project)"
    _stub_shellcheck "$proj"
    printf '#!/usr/bin/env bash\necho committed\n' > "$proj/tools/thing.sh"
    git -C "$proj" add . && git -C "$proj" commit -q -m "add a script"
    # The tree is CLEAN — this is exactly the state the old gate skipped.
    [ -z "$(git -C "$proj" status --porcelain)" ]

    output=$(cd "$proj" && PATH="$proj/stubbin:$PATH" \
        bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"

    python3 - <<PYEOF
import json
d = json.loads('''$output''')
failed = " ".join(d.get("gates_failed", []))
passed = " ".join(d.get("gates_passed", []))
assert "no .sh files changed" not in passed, (
    "gate skipped a committed script: " + passed
)
assert "shellcheck" in failed, d
PYEOF
}

@test "check-completion: shellcheck runs on an untracked .sh" {
    proj="$(_make_branch_project)"
    _stub_shellcheck "$proj"
    printf '#!/usr/bin/env bash\necho untracked\n' > "$proj/tools/loose.sh"

    output=$(cd "$proj" && PATH="$proj/stubbin:$PATH" \
        bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"

    python3 - <<PYEOF
import json
d = json.loads('''$output''')
assert "shellcheck" in " ".join(d.get("gates_failed", [])), d
PYEOF
}

@test "check-completion: a .sh deleted on this branch does not fail the gate" {
    # shellcheck cannot read a deleted file; failing for one that is
    # correctly gone would make the gate impossible to satisfy.
    proj="$(_make_branch_project)"
    printf '#!/usr/bin/env bash\necho doomed\n' > "$proj/tools/doomed.sh"
    git -C "$proj" add . && git -C "$proj" commit -q -m "add"
    git -C "$proj" rm -q "tools/doomed.sh"
    git -C "$proj" commit -q -m "remove it"

    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"

    python3 - <<PYEOF
import json
d = json.loads('''$output''')
assert not [f for f in d.get("gates_failed", []) if f.startswith("shellcheck")], d
PYEOF
}

@test "check-completion: a clean branch with no .sh changes still reports so" {
    # The complement — the fix must not make every run claim it checked
    # something, which would hide a genuinely skipped gate.
    proj="$(_make_branch_project)"

    output=$(cd "$proj" && bash tools/check-completion.sh 2>/dev/null || true)
    rm -rf "$proj"

    python3 - <<PYEOF
import json
d = json.loads('''$output''')
assert any(
    "no .sh files changed" in g for g in d.get("gates_passed", [])
), d
PYEOF
}
