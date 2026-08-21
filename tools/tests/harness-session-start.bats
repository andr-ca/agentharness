#!/usr/bin/env bats
#
# Tests for `tools/harness-session-start.sh` — a dirty-tree worktree
# reminder for consumer repos (issue #249, item 7). Guidance-that-prints,
# not enforcement: must never block (always exit 0), only warn.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../harness-session-start.sh"
    TARGET=$(mktemp -d)
    cd "$TARGET" || exit 1
    git init -q
    git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
}

teardown() {
    cd "$BATS_TEST_DIRNAME" || true
    rm -rf "$TARGET"
}

@test "harness-session-start: clean tree produces no warning" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "harness-session-start: dirty tree warns and still exits 0" {
    echo dirty > file.txt
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Working tree is dirty"* ]]
    [[ "$output" == *"git worktree add"* ]]
}

@test "harness-session-start: --base overrides the suggested base ref" {
    echo dirty > file.txt
    run bash "$SCRIPT" --base origin/develop
    [ "$status" -eq 0 ]
    [[ "$output" == *"origin/develop"* ]]
    [[ "$output" != *"origin/main"* ]]
}

@test "harness-session-start: already inside a linked worktree, dirty tree produces no warning" {
    git worktree add -q -b feature/test .worktrees/feature-test
    cd .worktrees/feature-test || exit 1
    echo dirty > file.txt
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "harness-session-start: outside any git repo is a silent no-op" {
    local outside
    outside="$(mktemp -d)"
    cd "$outside" || exit 1
    run bash "$SCRIPT"
    rm -rf "$outside"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "harness-session-start: --base with no value is a clear error" {
    run bash "$SCRIPT" --base
    [ "$status" -ne 0 ]
    [[ "$output" =~ "--base requires a value" ]]
}

@test "harness-session-start: an unknown flag is a clear error" {
    run bash "$SCRIPT" --bogus
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Unexpected argument" ]]
}

@test "harness-session-start: -h/--help prints usage and exits 0" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Usage:" ]]
}
