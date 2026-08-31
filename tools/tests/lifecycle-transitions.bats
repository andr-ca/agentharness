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
    HARNESS_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
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

@test "transition: update/audit fail clearly (not crash) once the recorded source path stops existing, and heal once it's restored" {
    # copy mode records source.path = HARNESS_DIR at init time (link/copy
    # mode have no --source override — see resolved_source_path). Simulate
    # the harness checkout having moved or been deleted since install by
    # rewriting the recorded path directly in state, the same way the
    # existing .agentharness-profile transition test simulates external
    # drift, rather than actually relocating this live checkout.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client none

    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
data = json.load(open(p))
data['source']['path'] = '/nonexistent/moved-away/agentharness'
json.dump(data, open(p, 'w'))
"

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "source path no longer exists" ]]

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Error: source path not found" ]]

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Error: source path not found" ]]

    # Restoring the recorded path to somewhere real heals both commands
    # without needing a fresh init.
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
data = json.load(open(p))
data['source']['path'] = '$HARNESS_ROOT'
json.dump(data, open(p, 'w'))
"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
}

@test "transition: --mode npm package-upgrade cycles through versions correctly (init → v1.0.0 → update to v2.0.0 → update back to v1.0.0)" {
    # P1-06: test the npm mode's package-upgrade story — when a consumer
    # upgrades their pinned npm version of agentharness, the next 'update'
    # should refresh the durable copy AND its package.json version field,
    # which 'audit --json' reports as package_source.durable_copy_version.
    # This test exercises a full upgrade→rollback→re-upgrade cycle using
    # isolated fixture "packages" (not this live repo) to avoid mutating
    # tracked files during the test.
    #
    # The preferred approach (see task description) is to use an env-var
    # override (AGENTHARNESS_NPM_HARNESS_DIR, added by P1-06) to point
    # copy_npm_durable_source at an isolated scratch copy rather than
    # HARNESS_DIR, the same way AGENTHARNESS_SUBMODULE_REMOTE works for
    # submodule mode.

    # Create two fixture "packages" with different versions, both containing
    # the minimal content npm mode actually needs: package.json and
    # .claude/skills/ (at least one skill so validation doesn't fail).
    local pkg_v1="$BATS_TMPDIR/agentharness-pkg-v1"
    local pkg_v2="$BATS_TMPDIR/agentharness-pkg-v2"

    mkdir -p "$pkg_v1/.claude/skills/committing" "$pkg_v2/.claude/skills/committing"

    # Each package needs its own package.json with version field.
    # Minimal valid package.json for this harness.
    python3 -c "
import json
pkg_v1 = '$pkg_v1/package.json'
with open(pkg_v1, 'w') as f:
    json.dump({'name': 'agentharness', 'version': '1.0.0', 'description': 'test fixture'}, f)

pkg_v2 = '$pkg_v2/package.json'
with open(pkg_v2, 'w') as f:
    json.dump({'name': 'agentharness', 'version': '2.0.0', 'description': 'test fixture'}, f)
"

    # Copy real skill content into both fixtures so the harness validates
    # (the skill symlink target itself doesn't matter, but the name must exist
    # in the source for validate_skills_filter to pass).
    cp "$HARNESS_ROOT/.claude/skills/committing/SKILL.md" "$pkg_v1/.claude/skills/committing/"
    cp "$HARNESS_ROOT/.claude/skills/committing/SKILL.md" "$pkg_v2/.claude/skills/committing/"

    # Also copy .github/hooks since init validates its presence too.
    mkdir -p "$pkg_v1/.github/hooks" "$pkg_v2/.github/hooks"
    touch "$pkg_v1/.github/hooks/pre-commit" "$pkg_v2/.github/hooks/pre-commit"

    # Init against v1.0.0 using the env override.
    export AGENTHARNESS_NPM_HARNESS_DIR="$pkg_v1"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills committing

    # Verify initial state: durable_copy_version should be 1.0.0
    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
    run python3 -c "
import json
d = json.loads('''$output''')
assert d['package_source']['durable_copy_version'] == '1.0.0', f\"Expected 1.0.0, got {d['package_source']['durable_copy_version']}\"
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]

    # Upgrade to v2.0.0: change the override and run update.
    export AGENTHARNESS_NPM_HARNESS_DIR="$pkg_v2"
    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Refreshing durable npm source" ]]

    # Verify the durable copy was refreshed: durable_copy_version should now be 2.0.0
    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
    run python3 -c "
import json
d = json.loads('''$output''')
assert d['package_source']['durable_copy_version'] == '2.0.0', f\"Expected 2.0.0, got {d['package_source']['durable_copy_version']}\"
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]

    # Rollback to v1.0.0: change the override back and update again.
    export AGENTHARNESS_NPM_HARNESS_DIR="$pkg_v1"
    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]

    # Verify the rollback worked: durable_copy_version should be back to 1.0.0
    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
    run python3 -c "
import json
d = json.loads('''$output''')
assert d['package_source']['durable_copy_version'] == '1.0.0', f\"Expected 1.0.0 after rollback, got {d['package_source']['durable_copy_version']}\"
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]

    # Cleanup (bats doesn't auto-clean BATS_TMPDIR in older versions).
    rm -rf "$pkg_v1" "$pkg_v2"
    unset AGENTHARNESS_NPM_HARNESS_DIR
}
