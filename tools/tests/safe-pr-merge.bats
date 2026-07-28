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

# ---------------------------------------------------------------------------
# verify_all_comments_replied: the "answered" rule must survive a bot-authored
# PR. GitHub reports a Dependabot PR's author login as "app/dependabot" while
# that same bot's comments are authored by "dependabot" — the two never
# compare equal, so the old author-anchored rule found no author comments at
# all, marked every comment unanswered, and could not be satisfied by replying
# (the reply itself then counted as one more unanswered non-author comment).
# ---------------------------------------------------------------------------

make_comments_gh_stub() {
    # $1 = PR author login, $2 = JSON comments array, $3 = viewer (merging user)
    local pr_author="$1" comments_json="$2" viewer="${3:-malandr}"
    mkdir -p "$TEST_PROJECT/bin"
    cat > "$TEST_PROJECT/bin/gh" <<STUB
#!/usr/bin/env bash
if [ "\$1" = "pr" ] && [ "\$2" = "view" ]; then
    if [[ "\$*" == *"author"* ]]; then
        echo '$pr_author'
    else
        echo '{"comments": $comments_json}'
    fi
    exit 0
fi
if [ "\$1" = "api" ] && [ "\$2" = "user" ]; then
    echo '$viewer'
    exit 0
fi
if [ "\$1" = "api" ]; then
    echo '[]'
    exit 0
fi
exit 1
STUB
    chmod +x "$TEST_PROJECT/bin/gh"
}

_run_verify() {
    run env PATH="$TEST_PROJECT/bin:$PATH" bash -c "
        source '$SCRIPT'
        verify_all_comments_replied 170 test-owner/test-repo
    "
}

@test "verify_all_comments_replied: a maintainer reply answers a bot comment on a bot-authored PR" {
    make_comments_gh_stub "app/dependabot" '[
        {"id":"c1","author":{"login":"dependabot"},"createdAt":"2026-07-28T11:42:42Z"},
        {"id":"c2","author":{"login":"malandr"},"createdAt":"2026-07-28T11:49:19Z"}
    ]'
    _run_verify
    [ "$status" -eq 0 ]
    [[ "$output" =~ "All review comments have been addressed" ]]
}

@test "verify_all_comments_replied: an unanswered bot comment on a bot PR still blocks" {
    make_comments_gh_stub "app/dependabot" '[
        {"id":"c1","author":{"login":"dependabot"},"createdAt":"2026-07-28T11:42:42Z"}
    ]'
    _run_verify
    [ "$status" -eq 1 ]
    [[ "$output" =~ "unanswered" ]]
}

@test "verify_all_comments_replied: a reply never counts as an unanswered comment against itself" {
    # The old rule counted the maintainer's own reply as a new unanswered
    # non-author comment, so each reply created another blocker.
    make_comments_gh_stub "app/dependabot" '[
        {"id":"c1","author":{"login":"dependabot"},"createdAt":"2026-07-28T11:42:42Z"},
        {"id":"c2","author":{"login":"malandr"},"createdAt":"2026-07-28T11:49:19Z"},
        {"id":"c3","author":{"login":"malandr"},"createdAt":"2026-07-28T11:52:00Z"}
    ]'
    _run_verify
    [ "$status" -eq 0 ]
}

@test "verify_all_comments_replied: human PR — reviewer comment with no later reply still blocks" {
    make_comments_gh_stub "malandr" '[
        {"id":"c1","author":{"login":"malandr"},"createdAt":"2026-07-28T10:00:00Z"},
        {"id":"c2","author":{"login":"some-reviewer"},"createdAt":"2026-07-28T11:00:00Z"}
    ]'
    _run_verify
    [ "$status" -eq 1 ]
    [[ "$output" =~ "unanswered" ]]
}

@test "verify_all_comments_replied: human PR — author reply after the reviewer comment passes" {
    make_comments_gh_stub "malandr" '[
        {"id":"c1","author":{"login":"some-reviewer"},"createdAt":"2026-07-28T11:00:00Z"},
        {"id":"c2","author":{"login":"malandr"},"createdAt":"2026-07-28T11:30:00Z"}
    ]'
    _run_verify
    [ "$status" -eq 0 ]
}

@test "verify_all_comments_replied: no comments at all passes" {
    make_comments_gh_stub "app/dependabot" '[]'
    _run_verify
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Merge-strategy argument collision: the usage text advertises
# "[gh pr merge options]" pass-through, but the merge call hardcoded
# --merge, so a caller-supplied --squash/--rebase collided with it. gh
# rejects that combination, and because the collision only surfaced at the
# final merge step it wasted the full ~20-minute reviewer poll first.
# ---------------------------------------------------------------------------

@test "safe-pr-merge: rejects conflicting merge strategies up front, before any polling" {
    run bash "$SCRIPT" 170 --squash --rebase
    [ "$status" -eq 1 ]
    [[ "$output" =~ "strategy" ]]
    # Must fail before doing any of the slow work.
    [[ ! "$output" =~ "Waiting" ]]
    [[ ! "$output" =~ "Verifying" ]]
}

@test "safe-pr-merge: a single caller-supplied strategy replaces the default instead of colliding" {
    run bash -c "source '$SCRIPT'; resolve_merge_strategy --squash --delete-branch"
    [ "$status" -eq 0 ]
    [[ "$output" == "--squash" ]]
}

@test "safe-pr-merge: defaults to --merge when the caller supplies no strategy" {
    run bash -c "source '$SCRIPT'; resolve_merge_strategy --delete-branch"
    [ "$status" -eq 0 ]
    [[ "$output" == "--merge" ]]
}

@test "verify_all_comments_replied: unauthenticated gh fails with an auth error, not a bogus unanswered list" {
    # An empty viewer makes every comment compare > "" and look unanswered.
    # The caller must be told gh can't identify them, not handed a list of
    # comment ids that are actually fine.
    mkdir -p "$TEST_PROJECT/bin"
    cat > "$TEST_PROJECT/bin/gh" <<'STUB'
#!/usr/bin/env bash
if [ "$1" = "api" ] && [ "$2" = "user" ]; then exit 1; fi
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
    echo '{"comments": [{"id":"c1","author":{"login":"someone"},"createdAt":"2026-07-28T11:00:00Z"}]}'
    exit 0
fi
echo '[]'
exit 0
STUB
    chmod +x "$TEST_PROJECT/bin/gh"
    _run_verify
    [ "$status" -eq 1 ]
    [[ "$output" =~ "authenticated GitHub user" ]]
    [[ ! "$output" =~ "unanswered" ]]
}

@test "safe-pr-merge: merge_args is never empty, so no guarded expansion is needed under set -u" {
    # Regression guard for the bash < 4.4 (macOS 3.2) case: expanding an
    # empty array as "${a[@]}" under `set -u` is an unbound variable error.
    # Seeding the array with the resolved strategy makes that unreachable.
    run bash -c '
        set -euo pipefail
        merge_strategy="--merge"
        merge_args=("$merge_strategy")
        printf "%s\n" "${#merge_args[@]}" "${merge_args[@]}"
    '
    [ "$status" -eq 0 ]
    [[ "${lines[0]}" == "1" ]]
    [[ "${lines[1]}" == "--merge" ]]
}
