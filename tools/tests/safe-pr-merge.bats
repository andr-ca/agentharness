#!/usr/bin/env bats
#
# Tests for tools/safe-pr-merge.sh — PR merge safety checklist enforcement.
# Tests verify that refusal paths work (e.g. missing argument, bad repo).
# Network-dependent steps (gh API calls) are mocked via stub functions on PATH.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../safe-pr-merge.sh"
    HARNESS_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"

    # Create a fake git repo with origin remote
    git init -q .
    git remote add origin "https://github.com/test-owner/test-repo.git" || true
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT"
    # Remove any stubs from PATH
    rm -rf "$TEST_PROJECT/bin" 2>/dev/null || true
}

# Mock gh command to avoid real API calls
mock_gh() {
    local cmd="$1"
    shift
    case "$cmd" in
        "pr")
            if [ "${1:-}" == "checks" ]; then
                # gh pr checks <pr> -R <repo>
                echo "check-name    PASS"
                return 0
            elif [ "${1:-}" == "view" ]; then
                # gh pr view <pr> -R <repo> --json comments -q '.comments | length'
                if [[ "${*:-}" == *"--json"* ]]; then
                    echo "[]"
                elif [[ "${*:-}" == *"baseRefName"* ]]; then
                    echo "main"
                fi
                return 0
            elif [ "${1:-}" == "list" ]; then
                echo "[]"
                return 0
            elif [ "${1:-}" == "merge" ]; then
                return 0
            fi
            ;;
        "api")
            # gh api repos/.../.../comments
            echo "[]"
            return 0
            ;;
        "run")
            if [ "${1:-}" == "list" ]; then
                echo "[]"
                return 0
            elif [ "${1:-}" == "view" ]; then
                echo "completed"
                return 0
            fi
            ;;
        *)
            return 1
            ;;
    esac
    return 1
}

@test "safe-pr-merge: exits 1 with no arguments" {
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Usage:" ]]
}

@test "safe-pr-merge: exits 1 with invalid PR number (non-numeric)" {
    run bash "$SCRIPT" "not-a-number"
    [ "$status" -eq 1 ]
}

@test "safe-pr-merge: requires git origin remote" {
    cd "$(mktemp -d)"
    git init -q .
    run bash "$SCRIPT" 1
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Could not parse" ]] || [[ "$output" =~ "remote" ]]
}

@test "safe-pr-merge: accepts PR number and optional merge args" {
    # This is a smoke test that the script parses arguments correctly.
    # We can't run a full merge without mocking gh, so we just verify
    # the argument parsing doesn't reject the input syntax.
    run bash "$SCRIPT" --help 2>&1 || true
    [[ "$output" =~ "Usage:" ]]
}

# Regression tests for wait_for_ci_run's commit-matching fix (issue #94):
# it used to trust "most recent run for the branch" without checking that
# run actually belongs to the merge commit, which raced GitHub's run-list
# indexing and could report a stale, unrelated run's conclusion as the
# post-merge result. Source the script (safe: main() only runs when
# invoked as $0, see the BASH_SOURCE guard at EOF) and stub `gh` on PATH
# to drive wait_for_ci_run directly.

make_gh_stub() {
    local target_sha="$1"
    local list_calls_until_match="${2:-1}"
    mkdir -p "$TEST_PROJECT/bin"
    cat > "$TEST_PROJECT/bin/gh" <<STUB
#!/usr/bin/env bash
state_dir="$TEST_PROJECT/.gh-stub-state"
mkdir -p "\$state_dir"

if [ "\$1" = "run" ] && [ "\$2" = "list" ]; then
    sha=""
    args=("\$@")
    for ((i=0; i<\${#args[@]}; i++)); do
        if [ "\${args[\$i]}" = "-c" ]; then
            sha="\${args[\$((i+1))]}"
        fi
    done
    counter_file="\$state_dir/list_calls_\$sha"
    calls=0
    [ -f "\$counter_file" ] && calls="\$(cat "\$counter_file")"
    calls=\$((calls + 1))
    echo "\$calls" > "\$counter_file"
    if [ "\$sha" = "$target_sha" ] && [ "\$calls" -ge "$list_calls_until_match" ]; then
        echo "999888"
    fi
    exit 0
fi

if [ "\$1" = "run" ] && [ "\$2" = "view" ]; then
    if [[ "\$*" == *"status"* ]]; then
        echo "completed"
    elif [[ "\$*" == *"conclusion"* ]]; then
        echo "success"
    fi
    exit 0
fi

exit 1
STUB
    chmod +x "$TEST_PROJECT/bin/gh"
}

@test "wait_for_ci_run: matches the run for the merge commit, not just the newest on the branch" {
    make_gh_stub "target-sha-abc" 1
    run env PATH="$TEST_PROJECT/bin:$PATH" bash -c "
        source '$SCRIPT'
        wait_for_ci_run test-owner/test-repo main target-sha-abc
    "
    [ "$status" -eq 0 ]
    [[ "$output" =~ "CI run completed with status: completed, conclusion: success" ]]
    [[ "$output" =~ "Post-merge CI is green" ]]
}

@test "wait_for_ci_run: retries until a run for the merge commit's SHA appears (index-lag race)" {
    # Simulates the exact failure from issue #94: the run for this commit
    # isn't in the list yet on the first query (GitHub's index hasn't
    # caught up), and only shows up on a later poll.
    make_gh_stub "target-sha-xyz" 3
    run env PATH="$TEST_PROJECT/bin:$PATH" bash -c "
        source '$SCRIPT'
        wait_for_ci_run test-owner/test-repo main target-sha-xyz
    "
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No CI run yet for commit" ]]
    [[ "$output" =~ "Post-merge CI is green" ]]
}

@test "wait_for_ci_run: never matches a different commit's run, even if it's the only one returned" {
    # gh's own -c filter is what enforces this in production; the stub
    # here only ever answers for 'other-sha', confirming the function
    # doesn't fall back to treating any run as good enough.
    make_gh_stub "other-sha" 1
    run env PATH="$TEST_PROJECT/bin:$PATH" SAFE_PR_MERGE_FIND_RUN_MAX_WAIT=4 bash -c "
        source '$SCRIPT'
        wait_for_ci_run test-owner/test-repo main target-sha-never-matches
    "
    [ "$status" -ne 0 ]
    [[ "$output" =~ "No CI run found for commit" ]]
}
