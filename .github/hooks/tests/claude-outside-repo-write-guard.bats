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
