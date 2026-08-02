#!/usr/bin/env bats
# Tests for .github/hooks/claude-outside-repo-write-guard.sh

setup() {
    TEST_ROOT="$(mktemp -d)"
    export TEST_ROOT
    (cd "$TEST_ROOT" && git init -q && git config user.email "test@test.com" && git config user.name "Test")
}

teardown() {
    rm -rf "$TEST_ROOT"
}

GUARD_SCRIPT="$BATS_TEST_DIRNAME/../claude-outside-repo-write-guard.sh"

_run_guard() {
    local payload="$1"
    printf '%s' "$payload" | bash "$GUARD_SCRIPT"
}

@test "guard: allows Write inside a git repo" {
    run _run_guard "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TEST_ROOT/newfile.txt\"}}"
    [ "$status" -eq 0 ]
}

@test "guard: allows Edit inside a git repo" {
    echo "content" > "$TEST_ROOT/existing.txt"
    run _run_guard "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TEST_ROOT/existing.txt\"}}"
    [ "$status" -eq 0 ]
}

@test "guard: allows writes under the system temp directory even when not in a repo" {
    tmp_root="$(python3 -c "import os, tempfile; print(os.path.realpath(tempfile.gettempdir()))")"
    scratch_dir="$(mktemp -d "$tmp_root/guard-test.XXXXXX")"
    run _run_guard "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$scratch_dir/scratch.txt\"}}"
    rm -rf "$scratch_dir"
    [ "$status" -eq 0 ]
}

@test "guard: blocks Write outside any repo and outside temp" {
    # The hook only inspects the payload's path; it never touches the
    # filesystem, so a fixed absolute path is safe with no side effects
    # and no dependence on $HOME (which could itself be under temp or
    # inside a repo in some environments).
    run _run_guard '{"tool_name":"Write","tool_input":{"file_path":"/guard-test-outside-repo-and-temp/.bashrc"}}'
    [ "$status" -eq 2 ]
    [[ "$output" == *"resolves outside any git repository"* ]]
}

@test "guard: allows Write inside a repo under a not-yet-created subdirectory" {
    run _run_guard "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TEST_ROOT/newdir/nested/file.txt\"}}"
    [ "$status" -eq 0 ]
}

@test "guard: no-ops for tools other than Write/Edit" {
    run _run_guard "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo hi >> ~/.bashrc\"}}"
    [ "$status" -eq 0 ]
}

@test "guard: no-ops when file_path is missing" {
    run _run_guard "{\"tool_name\":\"Write\",\"tool_input\":{}}"
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# The agent's own memory store must remain writable.
#
# Claude Code tells a session to write memories directly to
# <config-dir>/projects/<project>/memory/, which lives outside every git
# repository — so this guard blocked it and the memory feature silently
# stopped working. Nothing announces that: the write just fails, and
# every later session starts without the notes it should have had.
# ---------------------------------------------------------------------------

_run_guard_as_home() {
    # The exemption is anchored to one config root, so the fixture has to
    # declare which root it is pretending to be.
    printf '%s' "$2" | env HOME="$1" bash "$GUARD_SCRIPT"
}

@test "guard: allows a write to the per-project memory store" {
    run _run_guard_as_home /guard-test-home \
        '{"tool_name":"Write","tool_input":{"file_path":"/guard-test-home/.claude/projects/some-project/memory/a-fact.md"}}'
    [ "$status" -eq 0 ]
}

@test "guard: does not exempt another user's .claude tree" {
    # An unanchored */.claude/projects/*/memory/* pattern would exempt any
    # such directory anywhere on the filesystem, including someone else's
    # home — a wider hole than the exemption is worth.
    run _run_guard_as_home /guard-test-home \
        '{"tool_name":"Write","tool_input":{"file_path":"/home/otheruser/.claude/projects/p/memory/x.md"}}'
    [ "$status" -eq 2 ]
}

@test "guard: still blocks the global CLAUDE.md one level up" {
    # The exemption is for the memory store, not the config directory.
    # A global CLAUDE.md is exactly what this guard exists to protect.
    run _run_guard_as_home /guard-test-home \
        '{"tool_name":"Write","tool_input":{"file_path":"/guard-test-home/.claude/CLAUDE.md"}}'
    [ "$status" -eq 2 ]
}

@test "guard: still blocks settings.json in the config directory" {
    run _run_guard_as_home /guard-test-home \
        '{"tool_name":"Write","tool_input":{"file_path":"/guard-test-home/.claude/settings.json"}}'
    [ "$status" -eq 2 ]
}

@test "guard: still blocks a project directory that is not the memory store" {
    run _run_guard_as_home /guard-test-home \
        '{"tool_name":"Write","tool_input":{"file_path":"/guard-test-home/.claude/projects/some-project/history.jsonl"}}'
    [ "$status" -eq 2 ]
}

@test "guard: honours a relocated CLAUDE_CONFIG_DIR" {
    # Deliberately NOT under mktemp: everything below the system temp
    # directory is already allowed, so a temp path would pass without
    # the CLAUDE_CONFIG_DIR branch ever running. This path is outside
    # both the temp root and any repository, so only that branch can
    # allow it.
    config="/guard-test-relocated-config"
    run env CLAUDE_CONFIG_DIR="$config" bash "$GUARD_SCRIPT" <<< \
        "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$config/projects/p/memory/x.md\"}}"
    [ "$status" -eq 0 ]
}

@test "guard: a relocated config dir does not exempt its non-memory paths" {
    config="/guard-test-relocated-config"
    run env CLAUDE_CONFIG_DIR="$config" bash "$GUARD_SCRIPT" <<< \
        "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$config/settings.json\"}}"
    [ "$status" -eq 2 ]
}
