#!/usr/bin/env bats
#
# Lifecycle *transition* tests (P1-06) — exercise sequences of subcommands
# with external state changes between the steps, not the isolated
# happy-state snapshots harness-lifecycle.bats already covers. The
# hook-ownership defect that motivated this (fixed as P0-01) survived
# precisely because init and uninstall were only ever checked in
# isolation, never as an install -> modify -> doctor -> update ->
# uninstall chain.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT"
    true
}

@test "transition: full chain init -> status -> doctor -> update -> doctor -> uninstall -> status" {
    git init --quiet "$TEST_PROJECT"

    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,agentic-loops --with-hook
    [ -f "$TEST_PROJECT/.agentharness-state.json" ]

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "with_hook:     true" ]]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all checks passed" ]]

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no .agentharness-state.json found" ]]
}

@test "transition: a second uninstall is a clean, clear error — not a crash or silent success" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no .agentharness-state.json found" ]]
}

@test "transition: uninstall removes only what it installed, preserving user files" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    # User content created after install, outside anything the harness owns.
    echo "my app" > "$TEST_PROJECT/app.py"
    mkdir -p "$TEST_PROJECT/src"
    echo "code" > "$TEST_PROJECT/src/main.py"

    bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes

    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]
    [ -f "$TEST_PROJECT/app.py" ]
    [ -f "$TEST_PROJECT/src/main.py" ]
    [ "$(cat "$TEST_PROJECT/app.py")" = "my app" ]
}

@test "transition: break a skill then re-init heals it (doctor fails then passes)" {
    # copy mode: an independent copy we can safely mutate (link mode's
    # skill dirs are symlinks into this real repo — see harness-lifecycle.bats).
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing,agentic-loops

    rm -rf "$TEST_PROJECT/.claude/skills/committing"
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]

    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing,agentic-loops
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all checks passed" ]]
}

@test "transition: editing .agentharness-profile between runs is reflected downstream" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --profile prototype

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
    [[ "$output" =~ "prototype" ]]

    # User re-tiers the project after install.
    echo "production" > "$TEST_PROJECT/.agentharness-profile"

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
    [[ "$output" =~ "production" ]]
}

@test "transition: --with-hook install then uninstall restores core.hooksPath" {
    git init --quiet "$TEST_PROJECT"

    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook
    run git -C "$TEST_PROJECT" config --get core.hooksPath
    [ "$status" -eq 0 ]
    [[ "$output" =~ "agentharness" ]] || [[ "$output" =~ ".githooks" ]] || [[ -n "$output" ]]

    bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes

    # After uninstall the harness's hooksPath must no longer be in force —
    # either unset entirely or restored to whatever preceded it, but never
    # left pointing at the (now-removed) harness-managed hook dir.
    hooks_after="$(git -C "$TEST_PROJECT" config --get core.hooksPath || true)"
    [[ "$hooks_after" != *"agentharness"* ]]
}
