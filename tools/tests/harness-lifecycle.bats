#!/usr/bin/env bats
#
# Tests for the lifecycle subcommands (init/plan/status/doctor/audit/update/
# uninstall) added to tools/setup/harness-link.sh for P1-04. The pre-existing
# legacy-invocation behavior (harness-link.sh <target> [options]) is covered
# by tools/tests/harness-link.bats and is unchanged by this file.
#
# The submodule-mode tests are hermetic: they clone this checkout into a
# local bare remote (setup_local_bare_remote) and point submodule mode at
# it via AGENTHARNESS_SUBMODULE_REMOTE, so they need no network (P1-05).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"
    HARNESS_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    cd /
    rm -rf "$TEST_PROJECT"
    # Some tests must nest a target inside HARNESS_DIR itself (to reproduce
    # a dogfooding scenario) rather than under $TEST_PROJECT; clean it up
    # here so a failed assertion mid-test (which skips the rest of the
    # test body) can't leave it behind in the real checkout.
    [ -n "${DOGFOOD_TARGET:-}" ] && rm -rf "$DOGFOOD_TARGET"
    # Hermetic submodule tests create a local bare remote (P1-05) — clean
    # it up and drop the override so it can't leak into another test.
    [ -n "${BARE_REMOTE_PARENT:-}" ] && rm -rf "$BARE_REMOTE_PARENT"
    unset AGENTHARNESS_SUBMODULE_REMOTE
    unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0
    true
}

# GNU coreutils' 'timeout' isn't available on stock macOS — use python3
# (already a hard requirement of this harness) for a portable hang-guard
# instead, so a test asserting "this completes, doesn't hang" works the
# same on Linux CI and a contributor's Mac.
run_with_timeout() {
    local seconds="$1"
    shift
    python3 -c "
import subprocess, sys
try:
    sys.exit(subprocess.run(sys.argv[2:], timeout=float(sys.argv[1])).returncode)
except subprocess.TimeoutExpired:
    sys.exit(124)
" "$seconds" "$@"
}

# Point submodule mode at a local bare clone of this checkout instead of
# the network 'origin' (P1-05 hermeticity). A --bare clone carries every
# commit and tag (incl. v0.1.0, which the pin/rollback test rolls back
# to), so both `git submodule add` and the tag checkout resolve fully
# offline.
setup_local_bare_remote() {
    BARE_REMOTE_PARENT=$(mktemp -d)
    git clone --bare --quiet "$HARNESS_ROOT" "$BARE_REMOTE_PARENT/agentharness.git"
    export AGENTHARNESS_SUBMODULE_REMOTE="$BARE_REMOTE_PARENT/agentharness.git"
    # git blocks the 'file' transport for submodules by default
    # (CVE-2022-39253); re-allow it for this local-path remote via env so
    # every git the harness spawns in this test inherits it.
    export GIT_CONFIG_COUNT=1
    export GIT_CONFIG_KEY_0=protocol.file.allow
    export GIT_CONFIG_VALUE_0=always
}

@test "lifecycle: init writes a state file with mode, source, and skills" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching

    [ -f "$TEST_PROJECT/.agentharness-state.json" ]
    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
print(d['mode'])
print(sorted(d['skills']))
print(d['with_hook'])
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "copy" ]]
    [[ "$output" =~ "branching" ]]
    [[ "$output" =~ "committing" ]]
    [[ "$output" =~ "False" ]]
}

@test "lifecycle: legacy invocation (no subcommand) also writes a state file" {
    bash "$SCRIPT" "$TEST_PROJECT" --skills committing
    [ -f "$TEST_PROJECT/.agentharness-state.json" ]
}

@test "lifecycle: plan makes no filesystem changes" {
    run bash "$SCRIPT" plan "$TEST_PROJECT" --skills committing
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dry run" ]]
    [ -z "$(ls -A "$TEST_PROJECT")" ]
}

@test "lifecycle: init --dry-run is equivalent to plan" {
    run bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "dry run" ]]
    [ -z "$(ls -A "$TEST_PROJECT")" ]
}

@test "lifecycle: status reports mode, skills, and hook state" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mode:          copy" ]]
    [[ "$output" =~ "skills:        committing" ]]
    [[ "$output" =~ "with_hook:     true" ]]
}

@test "lifecycle: status fails clearly when never initialized" {
    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no .agentharness-state.json found" ]]
}

@test "lifecycle: doctor passes for a healthy install" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,agentic-loops

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all checks passed" ]]
}

@test "lifecycle: init warns about untracked files when target is a git repo (issue #88)" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m init

    run bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    [ "$status" -eq 0 ]
    [[ "$output" =~ "untracked file(s)" ]]
}

@test "lifecycle: init does not print the untracked-files note for a non-git target" {
    run bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "untracked file(s)" ]]
}

@test "lifecycle: plan/--dry-run never prints the untracked-files note" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m init

    run bash "$SCRIPT" plan "$TEST_PROJECT" --skills committing
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "untracked file(s)" ]]
}

@test "lifecycle: doctor warns when installed skills are untracked by git (issue #88)" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m init
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "untracked by git" ]]
    [[ "$output" =~ "all checks passed" ]]
}

@test "lifecycle: doctor stops warning once the installed skills are committed" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m init
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    git -C "$TEST_PROJECT" add -A
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet -m "add skills"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "untracked by git" ]]
    [[ "$output" =~ "all checks passed" ]]
}

@test "lifecycle: doctor fails when a bundled resource link is broken" {
    # --mode copy, deliberately: in --mode link, .claude/skills/<name> in
    # $TEST_PROJECT is itself a symlink to *this actual repo's* skill
    # directory — rm/ln through that path would mutate this repo's own
    # tracked files, not a disposable copy. copy mode gives us a real,
    # independent file to safely break.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills agentic-loops
    rm "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py"
    ln -s /nonexistent/agent_loop.py "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "broken bundled-resource link" ]]
}

@test "lifecycle: doctor fails when a skill directory is deleted out from under it" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    rm -rf "$TEST_PROJECT/.claude/skills/committing"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "SKILL.md not found" ]]
}

@test "lifecycle: audit reports skills available upstream but not installed" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "available upstream, not installed: branching" ]]
}

@test "lifecycle: audit --json reports the same drift as machine-readable output" {
    # P2-01: the review's "no machine-readable output" gap for the audit
    # capability. Same drift computation as the text-mode test above, just
    # asserted through the JSON structure instead of a substring match.
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
assert d['drift'] is True, d
assert 'branching' in d['available_not_installed'], d
assert d['installed_not_available'] == [], d
assert d['target'] == '$TEST_PROJECT', d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit --json reports publish_mode_active, selected_profile, and validation_commands (B5)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --profile internal
    touch "$TEST_PROJECT/.agentharness-publish-mode"

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
assert d['publish_mode_active'] is True, d
assert d['selected_profile'] == 'internal', d
cmds = {c['command']: c for c in d['validation_commands']}
assert cmds['tools/check.sh']['exists'] is True, d
assert cmds['tools/check.sh']['executable'] is True, d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit --json reports publish_mode_active false and profile default when neither is set" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
assert d['publish_mode_active'] is False, d
assert d['selected_profile'] == 'none (defaults to production)', d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit --json flags a validation command as missing when the harness checkout is missing it" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    source_path="$(python3 -c "
import json
print(json.load(open('$TEST_PROJECT/.agentharness-state.json'))['source']['path'])
")"
    # Point the recorded source at a fake harness checkout that's missing
    # one of the validation commands, without touching the real one.
    fake_source=$(mktemp -d)
    cp -r "$source_path/.claude" "$source_path/patterns" "$source_path/languages" "$source_path/frameworks" "$fake_source/" 2>/dev/null || true
    mkdir -p "$fake_source/tools/setup"
    cp "$source_path/tools/check.sh" "$fake_source/tools/check.sh"
    cp "$source_path/tools/setup/harness-link.sh" "$fake_source/tools/setup/harness-link.sh"
    # Deliberately omit verify-manifest.sh, verify-content-quality.py, generate-agents-md.sh
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
d = json.load(open(p))
d['source']['path'] = '$fake_source'
json.dump(d, open(p, 'w'))
"

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
cmds = {c['command']: c for c in d['validation_commands']}
assert cmds['tools/verify-manifest.sh']['exists'] is False, d
assert cmds['tools/check.sh']['exists'] is True, d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
    rm -rf "$fake_source"
}

@test "lifecycle: audit text mode shows selected profile, publish-authority flag, and validation commands" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --profile production
    touch "$TEST_PROJECT/.agentharness-publish-mode"

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Selected profile: production" ]]
    [[ "$output" =~ "Publish-authority flag active: true" ]]
    [[ "$output" =~ "Validation commands" ]]
    [[ "$output" =~ "tools/check.sh" ]]
    [[ "$output" =~ "verify-content-quality.py" ]]
}

# ---------------------------------------------------------------------------
# Validation-commands table: scope and executability (found by running audit
# on a real npm install of the published package).
#
# The table predates --mode npm and the .py helpers, and asserted two things
# that stopped being true: that the recorded source is always a whole harness
# checkout, and that every listed command is run directly.
# ---------------------------------------------------------------------------

@test "lifecycle: audit does not report the harness's own maintenance scripts as missing from an npm install" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    # The npm package ships only tools/setup/. Listing the harness repo's
    # maintenance scripts here marked every healthy npm install as broken.
    [[ "$output" != *"MISSING"* ]]
    [[ "$output" =~ "tools/setup/harness-link.sh" ]]
    [[ "$output" != *"tools/verify-manifest.sh"* ]]
    [[ "$output" != *"tools/generate-manifest.py"* ]]
    [[ "$output" =~ "ships only the installer" ]]
}

@test "lifecycle: audit --json omits full-checkout-only commands for an npm install" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
cmds = {c['command']: c for c in d['validation_commands']}
assert set(cmds) == {'tools/setup/harness-link.sh'}, cmds
assert cmds['tools/setup/harness-link.sh']['exists'] is True, cmds
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit still reports a genuinely missing command in a full checkout install" {
    # The scope filter must not swallow real breakage: link/copy/submodule
    # installs record a whole checkout, so every command stays in scope.
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    source_path="$(python3 -c "
import json
print(json.load(open('$TEST_PROJECT/.agentharness-state.json'))['source']['path'])
")"
    fake_source=$(mktemp -d)
    mkdir -p "$fake_source/tools/setup"
    cp "$source_path/tools/setup/harness-link.sh" "$fake_source/tools/setup/harness-link.sh"
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
d = json.load(open(p))
d['source']['path'] = '$fake_source'
json.dump(d, open(p, 'w'))
"

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "MISSING: tools/verify-manifest.sh" ]]
    rm -rf "$fake_source"
}

@test "lifecycle: audit does not warn that the python-invoked helpers are non-executable" {
    # tools/verify-content-quality.py and tools/generate-manifest.py are run
    # as 'python3 <path>' and are non-executable by design in this repo, so
    # the old blanket -x check warned on a pristine checkout.
    [ ! -x "$HARNESS_ROOT/tools/verify-content-quality.py" ]
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" != *"exists, not executable"* ]]
    [[ "$output" =~ "✓ tools/verify-content-quality.py" ]]
}

@test "lifecycle: audit --json marks python-invoked helpers as not requiring the executable bit" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
cmds = {c['command']: c for c in d['validation_commands']}
assert cmds['tools/verify-content-quality.py']['requires_executable'] is False, cmds
assert cmds['tools/generate-manifest.py']['requires_executable'] is False, cmds
assert cmds['tools/check.sh']['requires_executable'] is True, cmds
assert cmds['tools/setup/harness-link.sh']['requires_executable'] is True, cmds
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit still warns when a directly-run script loses its executable bit" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    source_path="$(python3 -c "
import json
print(json.load(open('$TEST_PROJECT/.agentharness-state.json'))['source']['path'])
")"
    fake_source=$(mktemp -d)
    mkdir -p "$fake_source/tools/setup"
    cp "$source_path/tools/check.sh" "$fake_source/tools/check.sh"
    cp "$source_path/tools/setup/harness-link.sh" "$fake_source/tools/setup/harness-link.sh"
    chmod -x "$fake_source/tools/check.sh"
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
d = json.load(open(p))
d['source']['path'] = '$fake_source'
json.dump(d, open(p, 'w'))
"

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "⚠ tools/check.sh (exists, not executable)" ]]
    rm -rf "$fake_source"
}

@test "lifecycle: audit points npm installs away from the policy check they cannot run" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    # verify-content-quality.py isn't in the package and there's no harness
    # checkout to run it in — telling an npm consumer to run it sends them
    # after a file that was never theirs.
    [[ "$output" =~ "Policy-conflict check: not available for --mode npm" ]]
    [[ "$output" != *"run 'python3 tools/verify-content-quality.py' in the harness checkout"* ]]
}

# ---------------------------------------------------------------------------
# Consumer-local check wrapper (issue #110, recommendations #1/#2/#3)
# ---------------------------------------------------------------------------

@test "lifecycle: init generates a consumer-local check wrapper for --mode link" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link
    wrapper="$TEST_PROJECT/.agentharness-bin/check"
    [ -x "$wrapper" ]
}

@test "lifecycle: --mode copy does not generate a check wrapper" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode copy
    [ ! -e "$TEST_PROJECT/.agentharness-bin" ]
}

@test "lifecycle: the generated check wrapper delegates to enforce-profile against the consumer project, not the harness" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link

    run bash "$TEST_PROJECT/.agentharness-bin/check"
    [ "$status" -eq 0 ]
    # $TEST_PROJECT has no pyproject.toml/go.mod/package.json -- the gate
    # should report "not implemented" for THIS project, not run (or claim
    # results for) the harness's own Python test suite.
    [[ "$output" =~ "enforce-profile: $TEST_PROJECT" ]]
    [[ "$output" =~ "implemented yet" ]]
}

@test "lifecycle: doctor warns (soft, not fail) when the check wrapper is missing for a non-copy mode" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link
    rm -f "$TEST_PROJECT/.agentharness-bin/check"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "consumer-local completion gate" ]]
    [[ "$output" =~ "missing" ]]
}

@test "lifecycle: doctor reports the check wrapper present when it exists" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "✓ consumer-local completion gate present" ]]
}

@test "lifecycle: update retroactively generates a missing check wrapper (issue #110)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link
    rm -f "$TEST_PROJECT/.agentharness-bin/check"
    [ ! -e "$TEST_PROJECT/.agentharness-bin/check" ]

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ -x "$TEST_PROJECT/.agentharness-bin/check" ]
}

@test "lifecycle: uninstall removes the check wrapper" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link
    [ -x "$TEST_PROJECT/.agentharness-bin/check" ]

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/.agentharness-bin" ]
}

@test "lifecycle: audit --json reports hooks, helper_commands, and can_mechanically_enforce (issue #110)" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link --with-hook

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
assert d['hooks']['with_hook'] is True, d
assert d['hooks']['coverage_hook'] is False, d
assert d['helper_commands']['check']['available'] is True, d
assert d['helper_commands']['check']['path'].endswith('.agentharness-bin/check'), d
assert d['can_mechanically_enforce'] is True, d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit --json reports can_mechanically_enforce false for --mode copy" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode copy

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
assert d['helper_commands']['check']['available'] is False, d
assert d['can_mechanically_enforce'] is False, d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: audit --json reports can_mechanically_enforce false when the wrapper's delegate target is missing (Copilot review)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode link
    source_path="$(python3 -c "
import json
print(json.load(open('$TEST_PROJECT/.agentharness-state.json'))['source']['path'])
")"
    # The wrapper itself stays present and executable -- only the script it
    # delegates to (at the recorded source) becomes unusable, e.g. a
    # partially-broken harness checkout.
    chmod -x "$source_path/tools/setup/harness-link.sh"

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]

    run python3 -c "
import json
d = json.loads('''$output''')
assert d['helper_commands']['check']['available'] is True, d
assert d['can_mechanically_enforce'] is False, d
print('ok')
"
    chmod +x "$source_path/tools/setup/harness-link.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]
}

@test "lifecycle: update declining the confirmation prompt does not regenerate the check wrapper (Copilot review)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching --mode link
    rm -f "$TEST_PROJECT/.agentharness-bin/check"
    # Force real drift (a removal) so update's confirmation prompt actually
    # fires instead of taking the no-op "(nothing to do)" branch.
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = 'committing'
json.dump(d, open(p, 'w'))
"

    run bash -c "echo n | bash '$SCRIPT' update '$TEST_PROJECT'"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Aborted" ]]
    [ ! -e "$TEST_PROJECT/.agentharness-bin/check" ]
}

@test "lifecycle: update adds newly-in-scope skills and refreshes the state file" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    # Simulate "install was set to track all skills, and a new one has since
    # been added upstream" by widening the recorded filter to null (no filter).
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = None
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "+ add: branching" ]]
    [ -e "$TEST_PROJECT/.claude/skills/branching" ]
}

@test "lifecycle: update removes skills no longer in scope" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = 'committing'
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "- remove: branching" ]]
    [ ! -e "$TEST_PROJECT/.claude/skills/branching" ]
    [ -e "$TEST_PROJECT/.claude/skills/committing" ]
}

@test "lifecycle: update declines to apply without confirmation" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    python3 -c "
import json
p = '$TEST_PROJECT/.agentharness-state.json'
with open(p) as f: d = json.load(f)
d['skills_filter'] = None
with open(p, 'w') as f: json.dump(d, f, indent=2)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" <<< "n"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Aborted" ]]
    [ ! -e "$TEST_PROJECT/.claude/skills/branching" ]
}

@test "lifecycle: update reports nothing-to-do when scope is unchanged" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "nothing to do" ]]
}

@test "lifecycle: uninstall reverses everything init recorded" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing,branching --with-hook --profile internal

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Uninstalled" ]]

    [ ! -e "$TEST_PROJECT/.claude/skills/committing" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/branching" ]
    [ ! -e "$TEST_PROJECT/.agents/skills/committing" ]
    [ ! -e "$TEST_PROJECT/.agents/skills/branching" ]
    [ ! -f "$TEST_PROJECT/.agentharness-profile" ]
    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]
    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "lifecycle: uninstall does not strand the empty directories it created" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]

    # Removing the last skill / the only harness-created file used to leave
    # .claude/, .agents/ and .github/ behind as empty husks.
    [ ! -d "$TEST_PROJECT/.claude" ]
    [ ! -d "$TEST_PROJECT/.agents" ]
    [ ! -d "$TEST_PROJECT/.github" ]
}

@test "lifecycle: uninstall preserves a directory holding anything the operator owns" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    mkdir -p "$TEST_PROJECT/.claude/skills/my-own-skill"
    echo "mine" > "$TEST_PROJECT/.claude/skills/my-own-skill/SKILL.md"
    echo "mine" > "$TEST_PROJECT/.claude/settings.json"
    mkdir -p "$TEST_PROJECT/.github/workflows"
    echo "mine" > "$TEST_PROJECT/.github/workflows/ci.yml"

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]

    # The prune is rmdir-only, so it stops at the first non-empty level and
    # can never take anything the operator put there with it.
    [ -f "$TEST_PROJECT/.claude/skills/my-own-skill/SKILL.md" ]
    [ -f "$TEST_PROJECT/.claude/settings.json" ]
    [ -f "$TEST_PROJECT/.github/workflows/ci.yml" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/committing" ]
}

@test "lifecycle: uninstall discloses the guarded-paths policy file it leaves behind" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    [ -f "$TEST_PROJECT/.agentharness-guarded-paths.json" ]

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]

    # Kept on purpose (the operator may have edited it), but an undisclosed
    # leftover is indistinguishable from a bug.
    [ -f "$TEST_PROJECT/.agentharness-guarded-paths.json" ]
    [[ "$output" =~ "Left in place: .agentharness-guarded-paths.json" ]]
}

@test "lifecycle: P0-01 regression — a pre-existing foreign core.hooksPath survives init, doctor, and uninstall" {
    # Direct reproduction of the gpt-5.6 third-pass P0-01 finding: init used
    # to record with_hook=true even when it declined to overwrite a
    # conflicting core.hooksPath, doctor only checked "is something set" (so
    # it passed against the untouched foreign value), and uninstall then
    # unconditionally unset core.hooksPath — deleting config the harness
    # never installed.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "preexisting/hooks"

    run bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "preexisting/hooks" ]

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
print(d['with_hook'])
print(d['hooks_path'])
"
    [[ "$output" =~ "False" ]]
    [[ "$output" =~ "None" ]]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all checks passed" ]]

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "preexisting/hooks" ]
}

@test "lifecycle: P0-01 regression — doctor fails if core.hooksPath is repointed after a real install" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook

    git -C "$TEST_PROJECT" config core.hooksPath "someone/else/changed/this"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "core.hooksPath has changed since install" ]]
}

@test "lifecycle: P0-01 regression — uninstall leaves a repointed core.hooksPath untouched" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook

    git -C "$TEST_PROJECT" config core.hooksPath "someone/else/changed/this"

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "someone/else/changed/this" ]
}

@test "lifecycle: #76 regression — doctor detects missing pre-merge-commit hook when with_hook is true" {
    git -C "$TEST_PROJECT" init --quiet
    # Use --mode copy to get actual files instead of symlinks
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy

    # Simulate the missing pre-merge-commit hook file (the issue #76 scenario)
    rm "$TEST_PROJECT/.github/hooks/pre-merge-commit"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "pre-merge-commit is missing" ]]
    [[ "$output" =~ "merge commits to trunk branches may bypass protection" ]]
}

@test "lifecycle: #149 regression — doctor's pre-merge-commit remediation shell-escapes a target path with spaces" {
    local spaced_project
    spaced_project="$(mktemp -d)/my project"
    mkdir -p "$spaced_project"
    git -C "$spaced_project" init --quiet
    bash "$SCRIPT" init "$spaced_project" --skills committing --with-hook --mode copy
    rm "$spaced_project/.github/hooks/pre-merge-commit"

    run bash "$SCRIPT" doctor "$spaced_project"
    [ "$status" -ne 0 ]
    # The raw unescaped path must never appear bare in the remediation line
    # (it would silently split into two args if copy-pasted); the escaped
    # form (backslash before the space) must.
    [[ "$output" != *"init $spaced_project --with-hook"* ]]
    [[ "$output" == *"${spaced_project// /\\ }"* ]]

    rm -rf "$(dirname "$spaced_project")"
}

@test "lifecycle: #76 regression — doctor passes when both pre-commit and pre-merge-commit hooks exist" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy

    # Verify doctor passes with both hooks present (the fixed scenario)
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "both pre-commit and pre-merge-commit hooks present" ]]
}

@test "lifecycle: #154 regression — doctor soft-warns when multi-agent-coordination skill is present but tools/agent-lock.sh is not" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills multi-agent-coordination --mode copy

    # A plain consumer install never gets tools/agent-lock.sh (it's this
    # harness's own dogfooding tool) — confirm the file is genuinely
    # absent, not merely non-executable, as the baseline here.
    [ ! -e "$TEST_PROJECT/tools/agent-lock.sh" ]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "tools/agent-lock.sh is missing or not executable" ]]
    [[ "$output" =~ "lock protocol this skill documents is inert" ]]
}

@test "lifecycle: #154 regression — doctor stays silent about agent-lock.sh when the skill isn't installed" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --mode copy

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" != *"agent-lock.sh is missing or not executable"* ]]
}

@test "lifecycle: #154 regression — doctor doesn't warn when tools/agent-lock.sh has been added by hand" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills multi-agent-coordination --mode copy
    mkdir -p "$TEST_PROJECT/tools"
    printf '#!/usr/bin/env bash\ntrue\n' > "$TEST_PROJECT/tools/agent-lock.sh"
    chmod +x "$TEST_PROJECT/tools/agent-lock.sh"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" != *"agent-lock.sh is missing or not executable"* ]]
}

@test "lifecycle: #155 regression — init --with-hook sets merge.ff=false" {
    git -C "$TEST_PROJECT" init --quiet
    run bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy
    [ "$status" -eq 0 ]
    [ "$(git -C "$TEST_PROJECT" config --get merge.ff)" = "false" ]
}

@test "lifecycle: #155 regression — doctor fails when with_hook is true but merge.ff isn't false" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy
    git -C "$TEST_PROJECT" config --unset merge.ff

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "merge.ff is not set to false" ]]
}

@test "lifecycle: #155 regression — doctor passes when merge.ff=false" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "merge.ff=false (fast-forward merges into trunk are blocked)" ]]
}

@test "lifecycle: #155 regression — uninstall unsets merge.ff when still exactly false" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy
    [ "$(git -C "$TEST_PROJECT" config --get merge.ff)" = "false" ]

    echo y | bash "$SCRIPT" uninstall "$TEST_PROJECT"
    [ -z "$(git -C "$TEST_PROJECT" config --get merge.ff 2>/dev/null)" ]
}

state_previous_merge_ff() {
    python3 -c "
import json
with open('$1/.agentharness-state.json') as f:
    print(json.load(f).get('previous_merge_ff'))
"
}

@test "lifecycle: #155 regression — uninstall restores an operator's pre-existing merge.ff instead of just unsetting it (Copilot review)" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config merge.ff only
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy
    [ "$(git -C "$TEST_PROJECT" config --get merge.ff)" = "false" ]
    [ "$(state_previous_merge_ff "$TEST_PROJECT")" = "only" ]

    echo y | bash "$SCRIPT" uninstall "$TEST_PROJECT"
    [ "$(git -C "$TEST_PROJECT" config --get merge.ff)" = "only" ]
}

@test "lifecycle: #155 regression — update carries previous_merge_ff forward instead of dropping it" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config merge.ff only
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy
    [ "$(state_previous_merge_ff "$TEST_PROJECT")" = "only" ]

    echo y | bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$(state_previous_merge_ff "$TEST_PROJECT")" = "only" ]

    echo y | bash "$SCRIPT" uninstall "$TEST_PROJECT"
    [ "$(git -C "$TEST_PROJECT" config --get merge.ff)" = "only" ]
}

@test "lifecycle: #155 acceptance test — a real fast-forward git merge into trunk is now blocked, not just direct commits" {
    # Direct reproduction of the issue #155 scenario: prevent-trunk-commit
    # blocks 'git commit' and 'git merge --no-ff' onto trunk, but a plain
    # fast-forward merge moves the ref with no commit for either hook to
    # fire on — the most ordinary way to "integrate a branch" silently
    # bypassed trunk protection. Uses real git merge, not a simulated hook.
    #
    # Whether a blocked, purely fast-forward-eligible merge leaves
    # MERGE_HEAD/merge-in-progress state (vs. just aborting cleanly) varies
    # by git version, so the two scenarios (blocked on trunk, allowed on a
    # feature branch) each get their own fresh repo instead of sharing one
    # and trying to clean up in between.
    local trunk trunk_rev0

    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=t@e.com -c user.name=t commit --quiet --allow-empty -m init
    trunk="$(git -C "$TEST_PROJECT" branch --show-current)"
    trunk_rev0="$(git -C "$TEST_PROJECT" rev-parse "$trunk")"

    git -C "$TEST_PROJECT" checkout -b feature/x --quiet
    echo "x" > "$TEST_PROJECT/x.txt"
    git -C "$TEST_PROJECT" add x.txt
    git -C "$TEST_PROJECT" -c user.email=t@e.com -c user.name=t commit --quiet -m "add x"
    git -C "$TEST_PROJECT" checkout "$trunk" --quiet

    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing --with-hook --mode copy

    # Before the fix this succeeded (fast-forward, no commit created, no
    # hook fired). With merge.ff=false it must now create a merge commit,
    # which pre-merge-commit blocks.
    run git -C "$TEST_PROJECT" merge feature/x
    [ "$status" -ne 0 ]
    [ "$(git -C "$TEST_PROJECT" rev-parse "$trunk")" = "$trunk_rev0" ]

    # A non-trunk branch is unaffected — merges there still work. Uses an
    # independent second fixture repo (see comment above) rather than
    # reusing $TEST_PROJECT after the blocked merge.
    local project2
    project2=$(mktemp -d)
    git -C "$project2" init --quiet
    git -C "$project2" -c user.email=t@e.com -c user.name=t commit --quiet --allow-empty -m init
    local trunk2
    trunk2="$(git -C "$project2" branch --show-current)"

    git -C "$project2" checkout -b feature/x --quiet
    echo "x" > "$project2/x.txt"
    git -C "$project2" add x.txt
    git -C "$project2" -c user.email=t@e.com -c user.name=t commit --quiet -m "add x"
    git -C "$project2" checkout -b integration --quiet "$trunk2"

    bash "$SCRIPT" init "$project2" --skills committing --with-hook --mode copy

    # This merge is real (not blocked) and, with merge.ff=false, creates an
    # actual merge commit — unlike the -c-scoped commits above, git needs a
    # repo-level identity for that, which a CI runner may not have globally.
    git -C "$project2" config user.email t@e.com
    git -C "$project2" config user.name t
    run git -C "$project2" merge feature/x
    [ "$status" -eq 0 ]
    rm -rf "$project2"
}

@test "doctor: reports a leftover crash journal" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    echo '{"plan_summary": ["AGENTS.md: upsert_block"]}' > "$TEST_PROJECT/.agentharness-state.pending.json"
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "pending" ]] || [[ "$output" =~ "journal" ]] || [[ "$output" =~ "interrupted" ]]
    rm -f "$TEST_PROJECT/.agentharness-state.pending.json"
}

@test "doctor: flags a managed block that has drifted from current render" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    sed -i 's/version=[^ ]* -->/version=0.0.1 -->/' "$TEST_PROJECT/AGENTS.md" 2>/dev/null || \
        sed -i '' 's/version=[^ ]* -->/version=0.0.1 -->/' "$TEST_PROJECT/AGENTS.md"
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [[ "$output" =~ "drift" ]]
}

@test "doctor: fails when pending journal is corrupted/unparseable" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    echo "not valid json" > "$TEST_PROJECT/.agentharness-state.pending.json"
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "corrupted" ]] || [[ "$output" =~ "parse" ]] || [[ "$output" =~ "failed to run" ]]
    rm -f "$TEST_PROJECT/.agentharness-state.pending.json"
}

@test "lifecycle: uninstall declines without confirmation" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" <<< "n"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Aborted" ]]
    [ -e "$TEST_PROJECT/.claude/skills/committing" ]
}

@test "lifecycle: uninstall fails clearly when never initialized" {
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -ne 0 ]
    [[ "$output" =~ "no .agentharness-state.json found" ]]
}

@test "lifecycle: --mode copy physically copies skill files, not symlinks" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing

    [ -f "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]
    [ ! -L "$TEST_PROJECT/.claude/skills/committing" ]
    [ ! -L "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]
}

@test "lifecycle: --mode copy also physically copies each skill into .agents/skills/ (P0-06)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing

    [ -f "$TEST_PROJECT/.agents/skills/committing/SKILL.md" ]
    [ ! -L "$TEST_PROJECT/.agents/skills/committing" ]
    [ ! -L "$TEST_PROJECT/.agents/skills/committing/SKILL.md" ]
}

@test "lifecycle: doctor also checks .agents/skills/, not just .claude/skills/ (P0-06)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --skills committing
    rm -rf "$TEST_PROJECT/.agents/skills/committing"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "SKILL.md not found" ]]
    [[ "$output" =~ ".agents/skills/committing" ]]
}

@test "lifecycle: --mode copy dereferences a skill's bundled-resource symlinks instead of copying them literally" {
    # Regression test: agentic-loops bundles agent_loop.py/test_agent_loop.py
    # as *relative* symlinks back to patterns/agentic-loops/ (see P1-03),
    # which only resolve from inside this checkout. A plain `cp -r` copied
    # those links literally into the target, where they pointed at a
    # patterns/ directory --mode copy never creates — found by running the
    # examples/{python,typescript,go}-project fixtures through every mode.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills agentic-loops

    [ ! -L "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py" ]
    [ -f "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py" ]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    run python3 -c "
import sys
sys.path.insert(0, '$TEST_PROJECT/.claude/skills/agentic-loops')
from agent_loop import Budget, ToolSpec, run_agent_loop
print('importable')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "importable" ]]
}

@test "lifecycle: --mode copy update reports no drift when content is unchanged" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "nothing to do" ]]
}

@test "lifecycle: --mode copy update detects when the copied content has diverged from source" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    # 'update' diffs the copy against the current source regardless of
    # which side actually changed — editing the consumer's copy is the
    # simplest way to produce a real divergence without touching this
    # repo's own tracked files.
    echo "local edit" >> "$TEST_PROJECT/.claude/skills/committing/SKILL.md"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "content changed upstream: committing" ]]
    # --yes applied the refresh, so the local edit is gone (overwritten from source).
    ! grep -q "local edit" "$TEST_PROJECT/.claude/skills/committing/SKILL.md"
}

@test "lifecycle: --mode copy --with-hook uninstall removes the copied hook files, not just core.hooksPath" {
    # Copilot review on PR #21: uninstall's hook-file cleanup only fired
    # when coverage_hook=true, leaving a plain '--mode copy --with-hook'
    # install's copied prevent-trunk-commit/pre-commit/pre-push files
    # behind after uninstall (core.hooksPath still got correctly unset).
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --with-hook

    [ -f "$TEST_PROJECT/.github/hooks/pre-push" ]

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Removed the copied hook files" ]]
    [ ! -e "$TEST_PROJECT/.github/hooks" ]
}

@test "lifecycle: --mode submodule adds this harness as a real submodule and symlinks from it" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    setup_local_bare_remote

    run bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Added agentharness as a submodule" ]]

    [ -e "$TEST_PROJECT/.agentharness/.git" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills/committing")
    [[ "$target" == *".agentharness/.claude/skills/committing" ]]
    [ -f "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]

    # Regression test: source.path/revision/remote must describe the
    # submodule *inside TEST_PROJECT*, not this harness dev checkout
    # (HARNESS_DIR). A real submodule-mode consumer never has HARNESS_DIR's
    # path on their machine — only their own submodule clone — and
    # recording HARNESS_DIR here previously made 'update'/'audit' compare
    # against the wrong tree (see gpt-5.6-review-status.md P1-06/07 CI
    # fixes: this caused 'update' to report phantom drift for skills that
    # exist in the live HARNESS_DIR checkout but not in whatever commit the
    # submodule actually cloned).
    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f: print(json.load(f)['source']['path'])
"
    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_PROJECT/.agentharness" ]
}

@test "lifecycle: --mode submodule with all skills reports no drift on immediate update" {
    # Regression test for the exact failure this repo's own CI hit
    # (fixture-matrix, submodule mode): init with the full default skill
    # set, then update right after — must be a no-op. It wasn't, because
    # 'update' used to recompute "available skills" from HARNESS_DIR
    # instead of the submodule it actually just installed from, so it saw
    # skills HARNESS_DIR has that the (possibly different-commit) submodule
    # didn't, and reported phantom drift.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    setup_local_bare_remote

    run bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule
    [ "$status" -eq 0 ]

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "(nothing to do)" ]]
}

@test "lifecycle: --mode submodule update/status/audit survive the whole project moving to a new path (issue #124)" {
    # source.path is recorded as an absolute path computed at install
    # time. If the project (submodule and all) is moved -- or cloned to
    # a different absolute path -- that recorded value goes stale, but
    # for submodule/npm modes the actual source is still right there at
    # <target>/.agentharness, just under the new location. update/audit
    # used to hard-fail with "recorded source path no longer exists"
    # instead of recomputing it from the current target.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    setup_local_bare_remote

    run bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing
    [ "$status" -eq 0 ]

    moved_project="$(dirname "$TEST_PROJECT")/moved-$(basename "$TEST_PROJECT")"
    mv "$TEST_PROJECT" "$moved_project"
    TEST_PROJECT="$moved_project"

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" != *"source path no longer exists"* ]]

    run bash "$SCRIPT" audit "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    run bash "$SCRIPT" update "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" != *"recorded source path no longer exists"* ]]

    # The self-healing part: after update, the recorded source.path in
    # state should reflect the new location, not the stale pre-move one.
    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f: print(json.load(f)['source']['path'])
"
    [ "$status" -eq 0 ]
    [ "$output" = "$TEST_PROJECT/.agentharness" ]
}

@test "lifecycle: --mode submodule uninstall removes the submodule cleanly" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    setup_local_bare_remote
    bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/.agentharness" ]
    run git -C "$TEST_PROJECT" submodule status
    [ -z "$output" ]
}

@test "lifecycle: --mode submodule supports pin, rollback, and re-upgrade against real history" {
    # P1-12: demonstrates the pin/upgrade/rollback story the submodule mode
    # promises (docs/INTEGRATION.md: "pinned via the submodule's own commit,
    # not a mutable external path") against this repo's actual git history,
    # not a simulated one. 'committing' has existed since v0.1.0, so it
    # resolves at any ancestor commit we roll back to.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    setup_local_bare_remote

    bash "$SCRIPT" init "$TEST_PROJECT" --mode submodule --skills committing
    submodule="$TEST_PROJECT/.agentharness"
    pinned_commit=$(git -C "$submodule" rev-parse HEAD)

    # Pin: doctor is healthy at the commit init recorded.
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    # Rollback: move the submodule to an ancestor commit by hand (the
    # documented, deliberately-manual way — see "Keeping Projects Updated"
    # in docs/INTEGRATION.md). The skill symlink still resolves because it
    # points into the submodule's working tree, not a specific blob. Roll
    # back to the v0.1.0 tag specifically (a real prior release, guaranteed
    # to carry the 'committing' skill per CHANGELOG.md) rather than an
    # arbitrary N-commits-back offset — this repo's history is full of
    # merge commits, so "~N" can land before a skill existed at all
    # instead of at an actual past release.
    rollback_commit=$(git -C "$submodule" rev-parse v0.1.0)
    git -C "$submodule" checkout --quiet "$rollback_commit"
    [ -f "$TEST_PROJECT/.claude/skills/committing/SKILL.md" ]
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    # Re-upgrade: move back to the tip commit, same mechanism.
    git -C "$submodule" checkout --quiet "$pinned_commit"
    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ "$(git -C "$submodule" rev-parse HEAD)" = "$pinned_commit" ]
}

@test "lifecycle: --mode npm regression — status/audit never leak the consumer's own git HEAD as the harness revision" {
    # Found running a real npm install inside a real consumer git repo — the
    # ordinary case, and the one shape none of the other --mode npm
    # fixtures in this file exercise (none of them git-init TEST_PROJECT).
    # .agentharness-pkg has no .git of its own (npm strips it), and plain
    # 'git -C .agentharness-pkg rev-parse HEAD' does upward directory
    # discovery rather than requiring one, so it silently resolved to
    # TEST_PROJECT's own HEAD and reported that as the harness's revision.
    git -C "$TEST_PROJECT" init --quiet
    echo x > "$TEST_PROJECT/marker"
    git -C "$TEST_PROJECT" add marker
    git -C "$TEST_PROJECT" -c user.email=t@t -c user.name=t commit --quiet -m init
    consumer_head="$(git -C "$TEST_PROJECT" rev-parse HEAD)"

    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills committing

    run bash "$SCRIPT" audit "$TEST_PROJECT" --json
    [ "$status" -eq 0 ]
    [[ "$output" != *"$consumer_head"* ]]
    run python3 -c "
import json
d = json.loads('''$output''')
assert d['current_revision'] == 'unknown', d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]

    run bash "$SCRIPT" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" != *"$consumer_head"* ]]
    [[ "$output" != *"source has moved on"* ]]
}

@test "lifecycle: --mode npm copies a durable source into the target instead of symlinking HARNESS_DIR (P0-02)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills agentic-loops

    [ -d "$TEST_PROJECT/.agentharness-pkg" ]
    [ ! -e "$TEST_PROJECT/.agentharness-pkg/.git" ]
    # npm mode's symlink is relative (issue #109 — an absolute symlink
    # here would still break after committing and cloning elsewhere,
    # even though the durable copy itself already travels with the
    # clone), so resolve it before checking where it actually points.
    # python3's os.path.realpath, not `readlink -f` (a GNU extension not
    # supported by BSD/macOS readlink — Copilot review, PR #125).
    target="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$TEST_PROJECT/.claude/skills/agentic-loops")"
    [[ "$target" == "$TEST_PROJECT/.agentharness-pkg"* ]]

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
print(d['source']['path'])
print(d['source']['revision'])
"
    [[ "$output" =~ "$TEST_PROJECT/.agentharness-pkg" ]]
    # package.json's version (e.g. 0.2.0), not a git SHA — meaningful for an
    # npm-distributed source where a consumer can look the version up.
    revision="$(echo "$output" | tail -1)"
    [[ "$revision" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

@test "lifecycle: --mode npm regression — self-copy guard covers a target nested under HARNESS_DIR, not just HARNESS_DIR itself" {
    # Copilot review on PR #20: the tar --exclude for copy_npm_durable_source
    # only matched "./$NPM_DURABLE_PATH" (a durable copy directly under
    # HARNESS_DIR). If 'target' is a SUBDIRECTORY of HARNESS_DIR (e.g.
    # dogfooding this repo with a nested scratch project), the durable
    # copy's real path relative to HARNESS_DIR is "./<subdir>/.agentharness-pkg",
    # which the old pattern didn't exclude — the tar walk could read back
    # the copy it was mid-write on.
    local harness_root="$BATS_TEST_DIRNAME/../.."
    DOGFOOD_TARGET="$harness_root/tmp-dogfood-target-$$"
    mkdir -p "$DOGFOOD_TARGET"

    run run_with_timeout 30 bash "$SCRIPT" init "$DOGFOOD_TARGET" --mode npm --skills agentic-loops
    [ "$status" -eq 0 ]
    [ -d "$DOGFOOD_TARGET/.agentharness-pkg" ]
    # The durable copy must not contain itself nested inside a copy of
    # itself — a bounded, sane size is evidence the self-inclusion never
    # happened (an unguarded run either fails or balloons/hangs).
    [ ! -e "$DOGFOOD_TARGET/.agentharness-pkg/.agentharness-pkg" ]
}

@test "lifecycle: --mode npm regression — doctor stays healthy after the original HARNESS_DIR-equivalent source disappears (P0-02)" {
    # Direct reproduction of the gpt-5.6 third-pass P0-02 acceptance
    # criterion: an npx-installed consumer must remain healthy after the
    # original process/package directory disappears. Simulates the real
    # npx flow — pack the actual package, extract it to a throwaway
    # "cache" directory, install from THAT extracted copy, then delete the
    # whole cache and confirm doctor still passes.
    #
    # Requires the runtime artifact cache to be seeded (.tool-cache/runtime-artifacts/).
    # In CI, the runtime-bootstrap-exact-four job seeds this; locally, run
    # `tools/runtime/seed-runtime-artifacts.sh` first, or skip with
    # CHECK_OFFLINE=1.
    local harness_root="$BATS_TEST_DIRNAME/../.."
    local tool_cache="$harness_root/.tool-cache/runtime-artifacts"
    if [ -z "$(ls "$tool_cache" 2>/dev/null)" ]; then
        skip "runtime artifact cache not seeded (.tool-cache/runtime-artifacts/ is empty); run tools/runtime/seed-runtime-artifacts.sh first"
    fi
    local cache pkg_tgz
    cache=$(mktemp -d)
    ( cd "$harness_root" && npm pack --silent --pack-destination "$cache" ) >/dev/null
    pkg_tgz=$(ls "$cache"/agentharness-toolkit-*.tgz)
    mkdir "$cache/extracted"
    tar xzf "$pkg_tgz" -C "$cache/extracted"

    node "$cache/extracted/package/bin/cli.js" init "$TEST_PROJECT" --skills agentic-loops

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]

    rm -rf "$cache"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "all checks passed" ]]
}

@test "lifecycle: --mode npm update refreshes the durable copy from the currently running package" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills agentic-loops

    # Simulate the durable copy having drifted from what's "currently
    # running" (e.g. an older npm version was installed, then a newer one
    # invoked update) by deleting a file from it — update should restore it
    # by re-copying from HARNESS_DIR, not just diff the copy against itself.
    rm "$TEST_PROJECT/.agentharness-pkg/README.md"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Refreshing durable npm source" ]]
    [ -f "$TEST_PROJECT/.agentharness-pkg/README.md" ]
}

@test "lifecycle: --mode npm update regression — symlinks a newly-in-scope skill, not just refreshes the durable copy" {
    # Copilot review on PR #20: cmd_update's re-sync loop only handled
    # mode in (link|submodule|copy) when creating symlinks for newly
    # in-scope skills — 'npm' fell through the case statement, silently
    # doing nothing, so an upgrade that introduces a new skill would never
    # actually link it even though 'update' reported success.
    #
    # Simulate "a newly-in-scope skill appeared" without an unrestricted
    # --skills filter (which would make every skill 'in scope' from the
    # start, masking the bug) by installing everything, then manually
    # dropping one skill from the recorded state + its symlink — from
    # 'update's point of view this looks exactly like a skill that just
    # became available upstream.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm

    rm "$TEST_PROJECT/.claude/skills/committing"
    python3 -c "
import json
path = '$TEST_PROJECT/.agentharness-state.json'
with open(path) as f:
    d = json.load(f)
d['skills'] = [s for s in d['skills'] if s != 'committing']
with open(path, 'w') as f:
    json.dump(d, f)
"

    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "+ add: committing" ]]
    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    # Relative symlink (issue #109) -- resolve before comparing. python3's
    # os.path.realpath, not `readlink -f` (GNU-only, not macOS/BSD).
    [ "$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$TEST_PROJECT/.claude/skills/committing")" = "$TEST_PROJECT/.agentharness-pkg/.claude/skills/committing" ]
}

@test "lifecycle: --mode npm uninstall removes the durable source copy" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills agentic-loops

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_PROJECT/.agentharness-pkg" ]
    [ ! -e "$TEST_PROJECT/.agentharness-state.json" ]
}

@test "lifecycle: --mode npm's durable copy is gitignored by the merged template (P0-02)" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --mode npm --skills agentic-loops

    run git -C "$TEST_PROJECT" check-ignore .agentharness-pkg
    [ "$status" -eq 0 ]
}

@test "cli.js: defaults 'init' to --mode npm when no --mode is given (P0-02)" {
    local harness_root="$BATS_TEST_DIRNAME/../.."
    run node "$harness_root/bin/cli.js" init "$TEST_PROJECT" --skills agentic-loops
    [ "$status" -eq 0 ]

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    print(json.load(f)['mode'])
"
    [ "$output" = "npm" ]
}

@test "cli.js: an explicit --mode is never overridden by the npm default" {
    local harness_root="$BATS_TEST_DIRNAME/../.."
    run node "$harness_root/bin/cli.js" init "$TEST_PROJECT" --skills agentic-loops --mode link
    [ "$status" -eq 0 ]

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    print(json.load(f)['mode'])
"
    [ "$output" = "link" ]
}

@test "cli.js: subcommands other than init/plan don't get --mode injected" {
    local harness_root="$BATS_TEST_DIRNAME/../.."
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills agentic-loops

    # 'status' takes no --mode flag at all; if cli.js injected one anyway,
    # harness-link.sh would treat it as an unexpected extra positional
    # argument and fail instead of reporting the recorded copy mode.
    run node "$harness_root/bin/cli.js" status "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "mode:          copy" ]]
}

@test "lifecycle: --with-coverage-hook generates a real, doctor-verified pre-push hook (P0-03)" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" init "$TEST_PROJECT" --skills agentic-loops --with-coverage-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Generated a coverage-aware pre-push hook" ]]

    [ -x "$TEST_PROJECT/.github/hooks/pre-push" ]
    grep -q "agentharness generated coverage hook" "$TEST_PROJECT/.github/hooks/pre-push"
    grep -q "enforce-profile" "$TEST_PROJECT/.github/hooks/pre-push"

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
assert d['with_hook'] is True, d
assert d['coverage_hook'] is True, d
print('ok')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ok" ]]

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "coverage-aware pre-push hook present" ]]
}

@test "lifecycle: --with-coverage-hook regression — doctor fails if the generated hook is hand-edited (marker removed)" {
    git -C "$TEST_PROJECT" init --quiet
    run bash "$SCRIPT" init "$TEST_PROJECT" --skills agentic-loops --with-coverage-hook
    [ "$status" -eq 0 ]

    echo "#!/bin/bash" > "$TEST_PROJECT/.github/hooks/pre-push"
    echo "exit 0" >> "$TEST_PROJECT/.github/hooks/pre-push"
    chmod +x "$TEST_PROJECT/.github/hooks/pre-push"

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "isn't the generated coverage hook" ]]
}

@test "lifecycle: --with-coverage-hook uninstall removes the generated hook files" {
    git -C "$TEST_PROJECT" init --quiet
    bash "$SCRIPT" init "$TEST_PROJECT" --skills agentic-loops --with-coverage-hook

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Removed the generated coverage-aware pre-push hook" ]]
    [ ! -e "$TEST_PROJECT/.github/hooks/pre-push" ]
    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "lifecycle: --with-coverage-hook regression — a real git push is blocked below the profile's coverage floor, and succeeds once fixed (P0-03 acceptance test)" {
    # Direct reproduction of the gpt-5.6 third-pass P0-03 acceptance
    # criterion: "a fixture below threshold fails a real consumer push
    # when the product says coverage is enforced." Uses a real bare
    # remote and a real 'git push', not a simulated hook invocation.
    local remote
    remote=$(mktemp -d)
    git init --bare --quiet "$remote"

    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" remote add origin "$remote"
    git -C "$TEST_PROJECT" -c user.email=t@e.com -c user.name=t commit --quiet --allow-empty -m init
    git -C "$TEST_PROJECT" push --quiet origin HEAD:main
    git -C "$TEST_PROJECT" checkout -b feature/x --quiet

    touch "$TEST_PROJECT/requirements.txt"
    cat > "$TEST_PROJECT/app.py" <<'PYEOF'
def covered():
    return 1

def uncovered_one():
    return 2

def uncovered_two():
    return 3
PYEOF
    cat > "$TEST_PROJECT/test_app.py" <<'PYEOF'
from app import covered

def test_covered():
    assert covered() == 1
PYEOF

    run bash "$SCRIPT" init "$TEST_PROJECT" --skills agentic-loops --with-coverage-hook --profile production
    [ "$status" -eq 0 ]
    git -C "$TEST_PROJECT" add -A
    git -C "$TEST_PROJECT" -c user.email=t@e.com -c user.name=t commit --quiet -m "add undercovered app"

    run git -C "$TEST_PROJECT" push origin feature/x
    [ "$status" -ne 0 ]
    [[ "$output" =~ "Coverage failure" ]] || [[ "$output" =~ "not reached" ]]

    # Fix coverage — the same push must now succeed.
    cat > "$TEST_PROJECT/test_app.py" <<'PYEOF'
from app import covered, uncovered_one, uncovered_two

def test_all():
    assert covered() == 1
    assert uncovered_one() == 2
    assert uncovered_two() == 3
PYEOF
    git -C "$TEST_PROJECT" add -A
    git -C "$TEST_PROJECT" -c user.email=t@e.com -c user.name=t commit --quiet -m "cover everything"

    run git -C "$TEST_PROJECT" push origin feature/x
    [ "$status" -eq 0 ]

    rm -rf "$remote"
}

@test "install lock: acquire and release round-trip" {
    run bash "$SCRIPT" __test_acquire_install_lock "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ -d "$TEST_PROJECT/.agentharness-install.lock" ]
    run bash "$SCRIPT" __test_release_install_lock "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [ ! -d "$TEST_PROJECT/.agentharness-install.lock" ]
}

@test "install lock: second acquire fails while first is held" {
    run bash "$SCRIPT" __test_acquire_install_lock "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    run bash "$SCRIPT" __test_acquire_install_lock "$TEST_PROJECT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "already in progress" ]] || [[ "$output" =~ "lock" ]]
    run bash "$SCRIPT" __test_release_install_lock "$TEST_PROJECT"
    [ "$status" -eq 0 ]
}

@test "init: renders managed block into pre-existing AGENTS.md" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    run bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    [ "$status" -eq 0 ]
    grep -q "agentharness:begin id=core-instructions" "$TEST_PROJECT/AGENTS.md"
    grep -q "# My project" "$TEST_PROJECT/AGENTS.md"
}

@test "init: re-running is idempotent on the managed block" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    local first_hash
    first_hash="$(sha256sum "$TEST_PROJECT/AGENTS.md" | cut -d' ' -f1)"
    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    local second_hash
    second_hash="$(sha256sum "$TEST_PROJECT/AGENTS.md" | cut -d' ' -f1)"
    [ "$first_hash" = "$second_hash" ]
}

@test "init: creates managed block in .github/copilot-instructions.md (parent dir doesn't exist)" {
    [ ! -d "$TEST_PROJECT/.github" ]
    run bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    [ "$status" -eq 0 ]
    [ -f "$TEST_PROJECT/.github/copilot-instructions.md" ]
    grep -q "agentharness:begin id=core-instructions" "$TEST_PROJECT/.github/copilot-instructions.md"
}

@test "init: releases lock if resolve_collisions_and_apply fails (regression: lock leak prevention)" {
    # Force a failure by creating a file with malformed markers (no end tag)
    # This causes classification HARD_FAIL, apply exits 1, but lock must be released
    echo "<!-- agentharness:begin id=core-instructions version=0.1.0 -->" > "$TEST_PROJECT/AGENTS.md"
    echo "no end marker" >> "$TEST_PROJECT/AGENTS.md"
    run bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    [ "$status" -ne 0 ]
    [ ! -d "$TEST_PROJECT/.agentharness-install.lock" ]
}

@test "init --dry-run prints plan without writing" {
    echo "# existing" > "$TEST_PROJECT/AGENTS.md"
    run bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" =~ "AGENTS.md" ]]
    ! grep -q "agentharness:begin" "$TEST_PROJECT/AGENTS.md"
}

@test "init does NOT create any .cursor/rules files (no fabricated whole-file surfaces)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    [ ! -e "$TEST_PROJECT/.cursor" ]
    [ ! -e "$TEST_PROJECT/.cursor/rules" ]
    [ ! -e "$TEST_PROJECT/.cursor/rules/testing.mdc" ]
}

@test "init: whole-file collision prompts and honors 'keep' via stdin" {
    # Test __test_resolve_collisions_and_apply with a synthetic whole-file surface
    mkdir -p "$TEST_PROJECT/.cursor/rules"
    echo "my own rule" > "$TEST_PROJECT/.cursor/rules/test-surface.txt"

    run bash -c "printf 'k\n' | bash '$SCRIPT' __test_resolve_collisions_and_apply '$TEST_PROJECT' '[{\"path\": \"$TEST_PROJECT/.cursor/rules/test-surface.txt\", \"is_block_surface\": false, \"content\": \"harness content\"}]' testid false false false"
    [ "$status" -eq 0 ]
    grep -q "my own rule" "$TEST_PROJECT/.cursor/rules/test-surface.txt"
}

@test "init --force overwrites whole-file collision with backup" {
    # Test __test_resolve_collisions_and_apply with --force flag
    mkdir -p "$TEST_PROJECT/.cursor/rules"
    echo "my own rule" > "$TEST_PROJECT/.cursor/rules/test-surface.txt"

    run bash "$SCRIPT" __test_resolve_collisions_and_apply "$TEST_PROJECT" '[{"path": "'$TEST_PROJECT'/.cursor/rules/test-surface.txt", "is_block_surface": false, "content": "harness content"}]' testid true false false
    [ "$status" -eq 0 ]
    ! grep -q "my own rule" "$TEST_PROJECT/.cursor/rules/test-surface.txt"
    grep -q "harness content" "$TEST_PROJECT/.cursor/rules/test-surface.txt"
    compgen -G "$TEST_PROJECT/.cursor/rules/test-surface.txt.pre-agentharness.*" >/dev/null
}

@test "init --keep-existing skips all collisions without prompting" {
    # Test __test_resolve_collisions_and_apply with --keep-existing flag
    mkdir -p "$TEST_PROJECT/.cursor/rules"
    echo "my own rule" > "$TEST_PROJECT/.cursor/rules/test-surface.txt"

    run bash "$SCRIPT" __test_resolve_collisions_and_apply "$TEST_PROJECT" '[{"path": "'$TEST_PROJECT'/.cursor/rules/test-surface.txt", "is_block_surface": false, "content": "harness content"}]' testid false false true
    [ "$status" -eq 0 ]
    grep -q "my own rule" "$TEST_PROJECT/.cursor/rules/test-surface.txt"
}

@test "resolve_collisions_and_apply returns 1 on stdin EOF without --force/--keep-existing (safety: unattended runs must not auto-overwrite)" {
    # Regression test: when stdin closes (EOF) without user response and no --force/--keep-existing,
    # the function must report the error and fail, not silently overwrite the consumer's file.
    # This safety behavior was violated in Task 13 and must not regress.
    mkdir -p "$TEST_PROJECT/.cursor/rules"
    echo "existing consumer content" > "$TEST_PROJECT/.cursor/rules/test.txt"

    run bash -c "bash '$SCRIPT' __test_resolve_collisions_and_apply '$TEST_PROJECT' '[{\"path\": \"$TEST_PROJECT/.cursor/rules/test.txt\", \"is_block_surface\": false, \"content\": \"harness content\"}]' id false false false < /dev/null"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "stdin closed" ]]
    # Verify the file was NOT overwritten
    grep -q "existing consumer content" "$TEST_PROJECT/.cursor/rules/test.txt"
}

@test "update: re-renders drifted managed block back to current content" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    sed -i 's/Installed skills/DRIFTED TEXT/' "$TEST_PROJECT/AGENTS.md" 2>/dev/null || \
        sed -i '' 's/Installed skills/DRIFTED TEXT/' "$TEST_PROJECT/AGENTS.md"
    run bash "$SCRIPT" update "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    grep -q "Installed skills" "$TEST_PROJECT/AGENTS.md"
}

@test "update --dry-run makes no filesystem or state changes (regression: PR #90 review)" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    local state_before
    state_before="$(cat "$TEST_PROJECT/.agentharness-state.json")"
    local agents_before
    agents_before="$(sha256sum "$TEST_PROJECT/AGENTS.md" | cut -d' ' -f1)"

    run bash "$SCRIPT" update "$TEST_PROJECT" --dry-run
    [ "$status" -eq 0 ]

    [ "$state_before" = "$(cat "$TEST_PROJECT/.agentharness-state.json")" ]
    [ "$agents_before" = "$(sha256sum "$TEST_PROJECT/AGENTS.md" | cut -d' ' -f1)" ]
}

@test "uninstall: removes managed block, preserves surrounding content" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    echo "custom line" >> "$TEST_PROJECT/AGENTS.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    ! grep -q "agentharness:begin" "$TEST_PROJECT/AGENTS.md"
    grep -q "# My project" "$TEST_PROJECT/AGENTS.md"
    grep -q "custom line" "$TEST_PROJECT/AGENTS.md"
}

@test "uninstall: restores backup for an unmodified overwritten file" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    mkdir -p "$TEST_PROJECT/.cursor/rules"
    echo "my own rule" > "$TEST_PROJECT/.cursor/rules/testing.mdc"
    # Seed a real overwritten_files state entry via the collision-resolution
    # helper (same one Task 13's tests use), targeting the state file that
    # init just created, so uninstall has something real to reverse.
    local surfaces_json
    surfaces_json="$(python3 -c "import json; print(json.dumps([{'path': '$TEST_PROJECT/.cursor/rules/testing.mdc', 'is_block_surface': False, 'content': 'harness content\n'}]))")"
    run bash "$SCRIPT" __test_resolve_collisions_and_apply "$TEST_PROJECT" "$surfaces_json" testid true false false
    [ "$status" -eq 0 ]
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    grep -q "my own rule" "$TEST_PROJECT/.cursor/rules/testing.mdc"
}

@test "uninstall: leaves post-install user edits in place with a warning" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    mkdir -p "$TEST_PROJECT/.cursor/rules"
    echo "my own rule" > "$TEST_PROJECT/.cursor/rules/testing.mdc"
    local surfaces_json
    surfaces_json="$(python3 -c "import json; print(json.dumps([{'path': '$TEST_PROJECT/.cursor/rules/testing.mdc', 'is_block_surface': False, 'content': 'harness content\n'}]))")"
    run bash "$SCRIPT" __test_resolve_collisions_and_apply "$TEST_PROJECT" "$surfaces_json" testid true false false
    [ "$status" -eq 0 ]
    echo "edited after install" > "$TEST_PROJECT/.cursor/rules/testing.mdc"
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    grep -q "edited after install" "$TEST_PROJECT/.cursor/rules/testing.mdc"
    [[ "$output" =~ "backup" ]] || [[ "$output" =~ "edited" ]]
}

@test "uninstall: called twice is a no-op the second time" {
    echo "# My project" > "$TEST_PROJECT/AGENTS.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -ne 0 ]  # require_state fails: no state file left — expected message, not a crash
    [[ "$output" =~ "no .agentharness-state.json" ]] || [[ "$output" =~ "init" ]]
}

@test "uninstall: a pre-existing EMPTY instructions file is never deleted" {
    # Data-loss regression. Provenance was first computed from whether the
    # file's CONTENT was empty, which cannot tell a missing file from a
    # 0-byte one the user touched as a placeholder — so uninstall deleted
    # their file. Unit tests missed it because they set the provenance flag
    # directly instead of exercising install's computation of it; only a
    # real install/uninstall cycle showed the loss.
    : > "$TEST_PROJECT/GEMINI.md"
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ -f "$TEST_PROJECT/GEMINI.md" ]
}

@test "uninstall: an instructions file the harness created is removed, not left empty" {
    # The other half: no husk for a file that only ever held our block.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    [ -f "$TEST_PROJECT/AGENTS.md" ]
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_PROJECT/AGENTS.md" ]
}

@test "uninstall: provenance survives an update, so a created file is still removed" {
    # update rewrites managed_blocks while the file now exists; recomputing
    # provenance there would flip "ours" to "theirs" and strand it forever.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing
    bash "$SCRIPT" update "$TEST_PROJECT" --yes
    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [ ! -f "$TEST_PROJECT/AGENTS.md" ]
}

# ============================================================================
# Issue #241: Client generation (build_surfaces_spec) regressions
# ============================================================================

@test "init --client codex with --skills committing generates only 1 skill in AGENTS.md (issue #241)" {
    # Regression: build_surfaces_spec crashed on HARNESS_DIR env lookup and
    # generate-clients used --output - which created a file named "-".
    # This test verifies skill-scoping walk-up works in init flow.
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client codex
    [ -f "$TEST_PROJECT/AGENTS.md" ]

    skill_count=$(grep -c '^- `.agents/skills/' "$TEST_PROJECT/AGENTS.md" || true)
    [ "$skill_count" -eq 1 ]
    grep -q "committing/SKILL.md" "$TEST_PROJECT/AGENTS.md"
    ! grep -q "accessibility/SKILL.md" "$TEST_PROJECT/AGENTS.md"
}

@test "init --client cursor generates exactly 2 rules: router + committing skill" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client cursor
    [ -f "$TEST_PROJECT/.cursor/rules/agentharness-router.mdc" ]
    [ -f "$TEST_PROJECT/.cursor/rules/committing.mdc" ]

    cursor_count=$(ls "$TEST_PROJECT/.cursor/rules/" 2>/dev/null | wc -l)
    [ "$cursor_count" -eq 2 ]
}

@test "init --client none creates no client-specific files (.cursor/rules, .kilo/rules)" {
    # Block-managed files (AGENTS.md, GEMINI.md, etc) are always created
    # as container files; --client none just means no generated content
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client none
    [ -f "$TEST_PROJECT/CLAUDE.md" ]
    # Block files still exist (they're the instruction container)
    [ -f "$TEST_PROJECT/AGENTS.md" ]
    # But client-specific directories do not
    [ ! -d "$TEST_PROJECT/.cursor/rules" ]
    [ ! -f "$TEST_PROJECT/.kilo/rules/agentharness.md" ]
}

@test "init --client cursor,kilo generates both Cursor rules and Kilo config" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client cursor,kilo
    [ -f "$TEST_PROJECT/.cursor/rules/agentharness-router.mdc" ]
    [ -f "$TEST_PROJECT/.cursor/rules/committing.mdc" ]
    [ -f "$TEST_PROJECT/.kilo/rules/agentharness.md" ]
    grep -q "committing/SKILL.md" "$TEST_PROJECT/.kilo/rules/agentharness.md"
}

@test "init --client cursor,kilo then init --client codex updates state correctly" {
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client cursor,kilo
    [ -d "$TEST_PROJECT/.cursor/rules" ]
    [ -f "$TEST_PROJECT/.kilo/rules/agentharness.md" ]

    # Reinit with just Codex (should not break)
    bash "$SCRIPT" init "$TEST_PROJECT" --mode copy --skills committing --client codex --force
    [ -f "$TEST_PROJECT/AGENTS.md" ]
}
