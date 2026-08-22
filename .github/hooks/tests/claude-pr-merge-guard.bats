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

# --- quoting: mention vs instruction ------------------------------------
#
# The first implementation stripped quoted spans with a regex, which got
# escapes wrong and false-positive blocked a command that only mentioned
# the phrase. Tokenizing with the shell's own rules (shlex) fixes the
# class; these lock the behaviour in.

@test "pr-merge guard: allows an escaped-quote mention" {
    run _run_guard "$(_cmd_payload 'echo "never run \"gh pr merge\" directly"')"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: allows the exact input that broke the regex version" {
    # Stripped the wrong span and left an exposed `gh pr merge`.
    run _run_guard "$(_cmd_payload 'echo "a\" gh pr merge "')"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: allows a single-quoted mention" {
    run _run_guard "$(_cmd_payload "echo 'do not gh pr merge by hand'")"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: allows a mention inside a gh pr comment body" {
    # The realistic case: replying to a review comment about this rule.
    run _run_guard "$(_cmd_payload 'gh pr comment 42 --body "use safe-pr-merge, not gh pr merge"')"
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: still blocks when the command follows a quoted string" {
    # Quoting elsewhere must not become a bypass.
    run _run_guard "$(_cmd_payload 'echo "about to merge" && gh pr merge 42')"
    [ "$status" -eq 2 ]
}

@test "pr-merge guard: unbalanced quotes fail open" {
    run _run_guard "$(_cmd_payload 'echo "unterminated')"
    [ "$status" -eq 0 ]
}

# --- cross-client portability -------------------------------------------
#
# The guard originally keyed on tool_name == 'Bash', which is Claude Code's
# name for the shell tool. Gemini CLI calls it run_shell_command and Codex
# uses its own naming, so a name check written against one client would
# silently allow everything on the others — installed, and doing nothing.
# Keying on the presence of tool_input.command is client-agnostic.

@test "pr-merge guard: blocks under Gemini's run_shell_command tool name" {
    run _run_guard '{"tool_name":"run_shell_command","tool_input":{"command":"gh pr merge 42"}}'
    [ "$status" -eq 2 ]
}

@test "pr-merge guard: blocks regardless of tool name when a command is present" {
    run _run_guard '{"tool_name":"some_future_shell","tool_input":{"command":"gh pr merge 42"}}'
    [ "$status" -eq 2 ]
}

@test "pr-merge guard: allows a tool call with no command field" {
    run _run_guard '{"tool_name":"read_file","tool_input":{"file_path":"/tmp/x"}}'
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: a non-string command does not crash the guard" {
    run _run_guard '{"tool_name":"Bash","tool_input":{"command":{"nested":"object"}}}'
    [ "$status" -eq 0 ]
}

# --- Cursor's flat payload shape -----------------------------------------
#
# Cursor's beforeShellExecution event passes {"command": "..."} with no
# tool_input wrapper at all — the other three clients all nest it. The
# guard checks the nested shape first, then falls back to a top-level
# command key, so it works unmodified across both payload families.

@test "pr-merge guard: blocks Cursor's flat command payload" {
    run _run_guard '{"command":"gh pr merge 42"}'
    [ "$status" -eq 2 ]
    [[ "$output" =~ "safe-pr-merge" ]]
}

@test "pr-merge guard: allows an unrelated command under Cursor's flat payload" {
    run _run_guard '{"command":"echo hello"}'
    [ "$status" -eq 0 ]
}

@test "pr-merge guard: a non-string top-level command does not crash the guard" {
    run _run_guard '{"command":{"nested":"object"}}'
    [ "$status" -eq 0 ]
}
