#!/usr/bin/env bats
# Tests for .github/hooks/prevent-trunk-commit
#
# Run locally:  bats .github/hooks/tests/prevent-trunk-commit.bats
# Requires: bats-core (https://github.com/bats-core/bats-core)

HOOK="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/prevent-trunk-commit"

setup() {
    TEST_REPO="$(mktemp -d)"
    cd "$TEST_REPO" || exit 1
}

teardown() {
    cd /tmp || exit 1
    rm -rf "$TEST_REPO"
}

install_hook() {
    cp "$HOOK" .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
}

@test "blocks the first commit on an unborn main branch" {
    git init -q -b main
    install_hook
    touch file.txt
    git add file.txt
    run git commit -m "test"
    [ "$status" -ne 0 ]
    [[ "$output" == *"CANNOT COMMIT DIRECTLY TO TRUNK BRANCH"* ]]
}

@test "blocks commits on master" {
    git init -q -b master
    install_hook
    touch file.txt
    git add file.txt
    run git commit -m "test"
    [ "$status" -ne 0 ]
}

@test "allows commits on a feature branch" {
    git init -q -b main
    install_hook
    touch file.txt
    git add file.txt
    run git commit -m "test" --no-verify
    [ "$status" -eq 0 ]
    git checkout -q -b feature/test
    touch file2.txt
    git add file2.txt
    run git commit -m "test2"
    [ "$status" -eq 0 ]
}

@test "blocks release/* branches (prefix match)" {
    git init -q -b main
    install_hook
    touch file.txt
    git add file.txt
    git commit -q -m "init" --no-verify
    git checkout -q -b release/1.2
    touch file2.txt
    git add file2.txt
    run git commit -m "test"
    [ "$status" -ne 0 ]
}

@test "does not block a branch merely prefixed like a trunk name (main-ish is not main)" {
    git init -q -b main-ish
    install_hook
    touch file.txt
    git add file.txt
    run git commit -m "test"
    [ "$status" -eq 0 ]
}
