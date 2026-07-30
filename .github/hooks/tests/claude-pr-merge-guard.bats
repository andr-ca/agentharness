#!/usr/bin/env bats
# Tests for .github/hooks/claude-pr-merge-guard.sh
#
# The PR-merge checklist in CLAUDE.md is ~60 lines of prose with no
# mechanical gate: tools/safe-pr-merge.sh implements it, but nothing
# required its use. An agent could run `gh pr merge` directly and skip the
# review wait, the comment fetch, and the post-merge CI verification
# entirely — and the only thing stopping it was reading the prose.
#
# This guard is the "gating beats thinning" move from the root-instruction
# inventory: once the rule is enforced, the prose describing it becomes
# compressible instead of load-bearing.

setup() {
    TEST_ROOT="$(mktemp -d)"
    export TEST_ROOT
    (cd "$TEST_ROOT" && git init -q \
        && git config user.email t@e.com && git config user.name t)
}

teardown() {
    rm -rf "$TEST_ROOT"
}

GUARD="$BATS_TEST_DIRNAME/../claude-pr-merge-guard.sh"

_run_guard() {
    printf '%s' "$1" | bash "$GUARD"
}

_cmd_payload() {
    printf '{"tool_name":"Bash","tool_input":{"command":%s}}' "$(
        python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
    )"
}

# --- what it must block -------------------------------------------------

@test "pr-merge guard: blocks a bare gh pr merge" {
    run _run_guard "$(_cmd_payload 'gh pr merge 42')"
    [ "$status" -eq 2 ]
    [[ "$output" =~ "safe-pr-merge" ]]
}

@test "pr-merge guard: blocks gh pr merge with flags" {
    run _run_guard "$(_cmd_payload 'gh pr merge 42 --squash --delete-branch')"
    [ "$status" -eq 2 ]
}

@test "pr-merge guard: blocks gh pr merge inside a compound command" {
    # The bypass that would matter most in practice.
    run _run_guard "$(_cmd_payload 'echo hi && gh pr merge 42')"
    [ "$status" -eq 2 ]
}

@test "pr-merge guard: blocks --admin, which bypasses branch protection" {
    run _run_guard "$(_cmd_payload 'gh pr merge 42 --admin')"
    [ "$status" -eq 2 ]
}

@test "pr-merge guard: explains what to run instead" {
    run _run_guard "$(_cmd_payload 'gh pr merge 42')"
    [[ "$output" =~ "tools/safe-pr-merge.sh" ]]
}

# --- what it must allow -------------------------------------------------

@test "pr-merge guard: allows safe-pr-merge.sh itself" {
    # Load-bearing: the wrapper's own internal `gh pr merge` runs in a
    # separate process, but the agent's invocation of the wrapper must
    # not be blocked by its own name matching.
    run _run_guard "$(_cmd_payload 'bash tools/safe-pr-merge.sh 42 --delete-branch')"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: allows other gh pr subcommands" {
    for sub in view checks list create comment edit; do
        run _run_guard "$(_cmd_payload "gh pr $sub 42")"
        [ "$status" -eq 0 ]
    done
}

@test "pr-merge guard: allows an unrelated command" {
    run _run_guard "$(_cmd_payload 'git status')"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: allows a command merely mentioning the phrase in text" {
    # Discussing the rule must not trip it — the same principle the
    # force-push doc check follows.
    run _run_guard "$(_cmd_payload 'echo "never run gh pr merge directly"')"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: allows a non-Bash tool call" {
    run _run_guard '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}'
    [ "$status" -eq 0 ]
}

# --- robustness ---------------------------------------------------------

@test "pr-merge guard: malformed payload does not block" {
    # Fails OPEN. A guard that blocks on unparseable input would make
    # every tool call hostage to a payload-shape change upstream.
    run _run_guard 'not json at all'
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: empty payload does not block" {
    run _run_guard ''
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: an explicit override is honoured and named" {
    run env AGENTHARNESS_PR_MERGE_BYPASS=1 bash -c \
        "printf '%s' '$(_cmd_payload 'gh pr merge 42')' | bash '$GUARD'"
    [ "$status" -eq 0 ]
}
