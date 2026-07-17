#!/usr/bin/env bats
# Tests for .github/hooks/pre-merge-commit
#
# Run locally:  bats .github/hooks/tests/pre-merge-commit.bats
# Requires: bats-core (https://github.com/bats-core/bats-core)

HOOK="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/pre-merge-commit"

setup() {
    TEST_REPO="$(mktemp -d)"
    cd "$TEST_REPO" || exit 1
}

teardown() {
    cd /tmp || exit 1
    rm -rf "$TEST_REPO"
}

# git init + a throwaway local identity. CI runners have no default git
# identity configured, and any commit (blocked or not) needs one before
# git will even invoke the pre-merge-commit hook, so every test needs this
# instead of relying on the environment already having one.
init_repo() {
    git init -q -b "$1"
    git config user.email "test@example.com"
    git config user.name "Test"
}

install_hook() {
    cp "$HOOK" .git/hooks/pre-merge-commit
    chmod +x .git/hooks/pre-merge-commit
}

@test "blocks a merge commit onto main branch" {
    init_repo main
    install_hook
    # Create an initial commit
    touch file1.txt
    git add file1.txt
    git commit -q -m "initial" --no-verify
    # Create a feature branch with a commit
    git checkout -q -b feature/test
    touch file2.txt
    git add file2.txt
    git commit -q -m "feature commit"
    # Try to merge back to main (should be blocked)
    git checkout -q main
    run git merge --no-ff feature/test -m "merge feature"
    [ "$status" -ne 0 ]
    [[ "$output" == *"CANNOT COMMIT DIRECTLY TO TRUNK BRANCH"* ]]
}

@test "blocks a merge commit onto master branch" {
    init_repo master
    install_hook
    # Create an initial commit
    touch file1.txt
    git add file1.txt
    git commit -q -m "initial" --no-verify
    # Create a feature branch with a commit
    git checkout -q -b feature/test
    touch file2.txt
    git add file2.txt
    git commit -q -m "feature commit"
    # Try to merge back to master (should be blocked)
    git checkout -q master
    run git merge --no-ff feature/test -m "merge feature"
    [ "$status" -ne 0 ]
}

@test "allows a merge commit onto a feature branch" {
    init_repo main
    install_hook
    # Create an initial commit
    touch file1.txt
    git add file1.txt
    git commit -q -m "initial" --no-verify
    # Create a feature branch with a commit
    git checkout -q -b feature/branch1
    touch file2.txt
    git add file2.txt
    git commit -q -m "branch1 commit"
    # Create another feature branch with a commit
    git checkout -q -b feature/branch2
    touch file3.txt
    git add file3.txt
    git commit -q -m "branch2 commit"
    # Merge branch2 into branch1 (should be allowed)
    git checkout -q feature/branch1
    run git merge --no-ff feature/branch2 -m "merge branch2"
    [ "$status" -eq 0 ]
}

@test "blocks a merge commit onto release/* branches" {
    init_repo main
    install_hook
    # Create an initial commit
    touch file1.txt
    git add file1.txt
    git commit -q -m "initial" --no-verify
    # Create a release branch
    git checkout -q -b release/1.2
    # Create a feature branch with a commit
    git checkout -q -b feature/test
    touch file2.txt
    git add file2.txt
    git commit -q -m "feature commit"
    # Try to merge back to release branch (should be blocked)
    git checkout -q release/1.2
    run git merge --no-ff feature/test -m "merge feature"
    [ "$status" -ne 0 ]
}
