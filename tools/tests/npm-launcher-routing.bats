#!/usr/bin/env bats
# The npm launcher (bin/cli.js) fronts two different backends: the bash
# lifecycle CLI (harness-link.sh) and the packaged Python core
# (dist/agentharness.pyz). It previously forwarded EVERY argument to bash,
# so a Python subcommand died with "Unexpected argument" — the packaged CLI
# advertised commands it could not reach.

setup() {
    HARNESS_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    CLI="$HARNESS_ROOT/bin/cli.js"
    TEST_PROJECT="$(mktemp -d)"
    cd "$TEST_PROJECT"
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT"
}

@test "launcher: bootstrap reaches the Python core, not harness-link.sh" {
    run node "$CLI" bootstrap plan --target-dir "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "capabilities" ]]
    [[ ! "$output" =~ "Unexpected argument" ]]
}

@test "launcher: every registered Python subcommand is routed" {
    # Guards the routing list against drift: a subcommand added to the
    # Python parser but not to PYTHON_SUBCOMMANDS would be silently sent
    # to bash and fail with a confusing usage error.
    for sub in bootstrap runtime github profile authority; do
        run node "$CLI" "$sub"
        [[ ! "$output" =~ "Unexpected argument" ]]
        [[ ! "$output" =~ "Usage: harness-link.sh" ]]
    done
}

@test "launcher: harness-link subcommands still go to bash" {
    # 'status' and 'plan' mean something on both sides; re-pointing them
    # would silently change behaviour for existing installs.
    run node "$CLI" status
    [[ "$output" =~ "agentharness-state.json" ]]
}

@test "launcher: the legacy target-directory form still works" {
    run node "$CLI" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "harness-link.sh" ]] || [[ "$output" =~ "Usage" ]]
}

@test "launcher: generate-clients does not get a bogus --mode npm injected (issue #240)" {
    # Found dogfooding: 'generate-clients' isn't 'init' or 'plan', so the
    # npm-mode-defaulting heuristic treated it as an unrecognized legacy
    # invocation and appended --mode npm -- a flag generate-clients does
    # not accept at all. Every real invocation died with "Unexpected
    # argument: --mode"; only --help (exempted separately) ever worked,
    # which is exactly why nothing caught this until a real npm consumer
    # ran the command as documented.
    git init --quiet "$TEST_PROJECT" >/dev/null 2>&1
    run node "$CLI" generate-clients "$TEST_PROJECT" --client cursor --dry-run
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "Unexpected argument" ]]
    [[ "$output" =~ "generate-clients" ]]
}

@test "launcher: audit-prs does not get a bogus --mode npm injected" {
    # Same class as generate-clients above -- audit-prs happened not to
    # error on the injected flag (it fails earlier, on 'not a GitHub
    # repo', before argument validation), but the injection itself is
    # still wrong and would misbehave for any future audit-prs option
    # that collides with --mode's argv position.
    run node "$CLI" audit-prs
    [[ ! "$output" =~ "Unexpected argument: --mode" ]]
}
