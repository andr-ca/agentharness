#!/usr/bin/env bats
#
# Tests for tools/setup/harness-link.sh — verifies integration script works
#

setup() {
    # Resolve the script under test relative to this test file, not a
    # hardcoded developer path, so this runs in CI and on any machine.
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"

    # Create a temporary directory for test projects
    TEST_PROJECT=$(mktemp -d)
    cd "$TEST_PROJECT"
}

teardown() {
    # Clean up test directory
    cd /
    rm -rf "$TEST_PROJECT"
}

# sha256sum isn't available by default on macOS (it uses `shasum` instead)
# — python3 is already a hard requirement for harness-link.sh itself, so
# it's a portable hash implementation both linux and macOS actually have.
file_hash() {
    python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1"
}

@test "harness-link.sh: help message shows usage" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Usage" ]]
}

@test "harness-link.sh: requires target project path argument" {
    run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "target project directory is required" ]]
}

@test "harness-link.sh: symlinks individual skills into .claude/skills/" {
    bash "$SCRIPT" "$TEST_PROJECT" --mode link

    # The script symlinks each skill individually into .claude/skills/,
    # it does not symlink .claude/skills/ itself.
    [ -d "$TEST_PROJECT/.claude/skills" ]
    [ ! -L "$TEST_PROJECT/.claude/skills" ]
    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    target=$(readlink "$TEST_PROJECT/.claude/skills/committing")
    [[ "$target" == *"/.claude/skills/committing" ]]
}

@test "harness-link.sh: also symlinks each skill into .agents/skills/ for Codex's real on-demand discovery (P0-06)" {
    bash "$SCRIPT" "$TEST_PROJECT" --mode link

    [ -d "$TEST_PROJECT/.agents/skills" ]
    [ ! -L "$TEST_PROJECT/.agents/skills" ]
    [ -L "$TEST_PROJECT/.agents/skills/committing" ]
    target=$(readlink "$TEST_PROJECT/.agents/skills/committing")
    [[ "$target" == *"/.claude/skills/committing" ]]
    # Same source as .claude/skills/committing — not two independent copies.
    [ -e "$TEST_PROJECT/.agents/skills/committing/SKILL.md" ]
    diff -q "$TEST_PROJECT/.agents/skills/committing/SKILL.md" "$TEST_PROJECT/.claude/skills/committing/SKILL.md"
}

@test "harness-link.sh: --skills filters which skills are linked" {
    bash "$SCRIPT" "$TEST_PROJECT" --mode link --skills committing,branching

    [ -L "$TEST_PROJECT/.claude/skills/committing" ]
    [ -L "$TEST_PROJECT/.claude/skills/branching" ]
    [ ! -e "$TEST_PROJECT/.claude/skills/python-conventions" ]
}

@test "harness-link.sh: agentic-loops skill is importable standalone (only that skill linked)" {
    # Regression test for P1-03: a skill's own bundled code must resolve
    # in a consumer that only linked *this one* skill, not the whole
    # patterns/ tree (which harness-link.sh never symlinks). Previously
    # agentic-loops/SKILL.md referenced "patterns/agentic-loops/agent_loop.py"
    # — a path that doesn't exist anywhere in a consumer project, symlink
    # depth or not. Fixed by bundling agent_loop.py/test_agent_loop.py as
    # relative symlinks inside the skill's own directory.
    bash "$SCRIPT" "$TEST_PROJECT" --skills agentic-loops

    [ -e "$TEST_PROJECT/.claude/skills/agentic-loops/agent_loop.py" ]
    [ -e "$TEST_PROJECT/.claude/skills/agentic-loops/test_agent_loop.py" ]

    run python3 -c "
import sys
sys.path.insert(0, '$TEST_PROJECT/.claude/skills/agentic-loops')
from agent_loop import Budget, ToolSpec, run_agent_loop
print('importable')
"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "importable" ]]
}

@test "harness-link.sh: --skills rejects path traversal atomically instead of installing a partial set (P0-04)" {
    # Regression test: "../../patterns" (or an absolute path) used to
    # resolve straight through to SRC="$SKILLS_SRC/../../patterns",
    # symlinking an arbitrary harness path into the target project's
    # .claude/skills/. See docs/operational/reviews/gpt-5.6-review-status.md.
    #
    # Originally fixed by silently skipping the bad name (exit 0, partial
    # install) — the gpt-5.6 third-pass review correctly flagged that as its
    # own problem: automation can't distinguish "everything requested was
    # installed" from "one bad name got silently dropped." Now the whole
    # command aborts before touching the filesystem, and nothing traversal-
    # shaped should exist anywhere.
    run bash "$SCRIPT" "$TEST_PROJECT" --skills "../../patterns,committing"

    [ "$status" -ne 0 ]
    [[ "$output" =~ "invalid skill name: '../../patterns'" ]]
    [ ! -e "$TEST_PROJECT/.claude/skills" ]
}

@test "harness-link.sh: --skills with a typo fails atomically instead of producing an empty 'successful' install (P0-04)" {
    run bash "$SCRIPT" "$TEST_PROJECT" --skills "definitely-not-a-skill"

    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown skill: 'definitely-not-a-skill'" ]]
    [ ! -f "$TEST_PROJECT/.agentharness-state.json" ]
    [ ! -e "$TEST_PROJECT/.claude" ]
}

@test "harness-link.sh: --skills none is the sanctioned way to install zero skills (P0-04)" {
    run bash "$SCRIPT" "$TEST_PROJECT" --skills none
    [ "$status" -eq 0 ]

    run python3 -c "
import json
with open('$TEST_PROJECT/.agentharness-state.json') as f:
    d = json.load(f)
print(len(d['skills']))
"
    [ "$output" = "0" ]
}

@test "harness-link.sh: plan (--dry-run) reports the same invalid-skill failure init would, before mutating anything" {
    run bash "$SCRIPT" plan "$TEST_PROJECT" --skills "definitely-not-a-skill"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown skill: 'definitely-not-a-skill'" ]]
    [ ! -e "$TEST_PROJECT/.claude" ]
}

@test "harness-link.sh: merges .gitignore.template into .gitignore" {
    # Pre-create a .gitignore with some content
    echo "node_modules/" > "$TEST_PROJECT/.gitignore"

    bash "$SCRIPT" "$TEST_PROJECT"

    # Check that .gitignore exists and contains content from both original and template
    [ -f "$TEST_PROJECT/.gitignore" ]
    grep -q "node_modules" "$TEST_PROJECT/.gitignore"
    grep -q "\.env" "$TEST_PROJECT/.gitignore"  # From template
}

@test "harness-link.sh: --with-hook sets core.hooksPath in an existing git repo" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --with-hook

    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]
}

@test "harness-link.sh: --with-hook works against a linked worktree, not just the main checkout" {
    # Regression test: a worktree's .git is a *file* (gitdir: ...), not a
    # directory, so `[ -d "$TARGET/.git" ]` used to treat every worktree
    # as "not a git repo" and silently skip hook installation.
    main_repo=$(mktemp -d)
    git -C "$main_repo" init --quiet
    git -C "$main_repo" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m "init"
    worktree_dir="$TEST_PROJECT/worktree"
    git -C "$main_repo" worktree add --quiet "$worktree_dir" --detach >/dev/null

    [ -f "$worktree_dir/.git" ]
    [ ! -d "$worktree_dir/.git" ]

    run bash "$SCRIPT" "$worktree_dir" --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Installed" ]]
    hooks_path=$(git -C "$worktree_dir" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]

    git -C "$main_repo" worktree remove --force "$worktree_dir" 2>/dev/null || true
    rm -rf "$main_repo"
}

@test "harness-link.sh: --with-hook refuses to overwrite a different existing core.hooksPath" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "some/other/hooks" ]
}

@test "harness-link.sh: --mode copy --with-hook does not treat an equivalent relative core.hooksPath as a conflict" {
    # Copilot review on PR #21: core.hooksPath can be recorded as a
    # relative path (git resolves it relative to the work tree at run
    # time), but the conflict check compared it as a raw string against
    # our always-absolute intended hooks_path — an equivalent, correct
    # relative value was wrongly treated as a conflicting hooksPath.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath ".github/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --mode copy --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"already has a different core.hooksPath"* ]]
    [[ "$output" =~ "Installed trunk-protection hook" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "$TEST_PROJECT/.github/hooks" ]
}

@test "harness-link.sh: --mode copy --with-hook normalizes a './'-prefixed, trailing-slash hooksPath before comparing (Copilot review round 4)" {
    # Plain string concatenation isn't enough: "./.github/hooks/" and
    # "$TEST_PROJECT/.github/hooks" are the same directory to git but
    # different strings — normalize both sides before comparing.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "./.github/hooks/"

    run bash "$SCRIPT" "$TEST_PROJECT" --mode copy --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" != *"already has a different core.hooksPath"* ]]
    [[ "$output" =~ "Installed trunk-protection hook" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "$TEST_PROJECT/.github/hooks" ]
}

@test "harness-link.sh: --with-hook still detects a genuinely different relative core.hooksPath as a conflict" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --mode copy --with-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "some/other/hooks" ]
}

@test "harness-link.sh: generated coverage hook's harness-link.sh path is shell-escaped against injection" {
    # Copilot review on PR #21: the generated pre-push script's
    # HARNESS_LINK=... assignment embeds this path %q-quoted but
    # otherwise unquoted-on-the-left — an unescaped path containing
    # shell metacharacters would be evaluated as a command when the
    # generated hook later runs.
    git -C "$TEST_PROJECT" init --quiet
    local evil_dir="$TEST_PROJECT/../evil-\$(touch $TEST_PROJECT/PWNED)-dir"
    mkdir -p "$evil_dir"

    (
        source "$SCRIPT" 2>/dev/null || true
        mkdir -p "$TEST_PROJECT/.github/hooks"
        generate_coverage_pre_push "$TEST_PROJECT" "$evil_dir/harness-link.sh"
    )

    bash -n "$TEST_PROJECT/.github/hooks/pre-push"
    run bash "$TEST_PROJECT/.github/hooks/pre-push"
    [ ! -e "$TEST_PROJECT/PWNED" ]

    rm -rf "$evil_dir"
}

@test "harness-link.sh: --with-coverage-hook refusing a conflicting core.hooksPath leaves no generated hook files behind" {
    # Copilot review on PR #21: the generated/copied hook files used to be
    # written to $target/.github/hooks BEFORE the core.hooksPath conflict
    # check ran, so a declined install (with_hook=false recorded) could
    # still leave real files behind as a side effect. Verify the decline
    # path is now genuinely a no-op on the filesystem, not just on state.
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --with-coverage-hook
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different core.hooksPath" ]]
    [ ! -e "$TEST_PROJECT/.github/hooks" ]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [ "$hooks_path" = "some/other/hooks" ]
}

@test "harness-link.sh: --with-hook --force overwrites a different existing core.hooksPath" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" config core.hooksPath "some/other/hooks"

    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook --force
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Overwrote existing core.hooksPath" ]]
    hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)
    [[ "$hooks_path" == *".github/hooks" ]]
}

@test "harness-link.sh: --with-hook is a no-op (with warning) when target isn't a git repo yet" {
    run bash "$SCRIPT" "$TEST_PROJECT" --with-hook

    [ "$status" -eq 0 ]
    [[ "$output" =~ "not a git repo" ]]
    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "harness-link.sh: without --with-hook, core.hooksPath is left untouched" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT"

    run git -C "$TEST_PROJECT" config core.hooksPath
    [ "$status" -ne 0 ]
}

@test "harness-link.sh: is idempotent (run twice safely, same resulting state)" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --mode link --with-hook
    [ "$status" -eq 0 ]
    initial_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    initial_gitignore=$(file_hash "$TEST_PROJECT/.gitignore")
    initial_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    # Run again
    run bash "$SCRIPT" "$TEST_PROJECT" --mode link --with-hook
    [ "$status" -eq 0 ]
    final_links=$(find "$TEST_PROJECT/.claude" -type l | sort)
    final_gitignore=$(file_hash "$TEST_PROJECT/.gitignore")
    final_hooks_path=$(git -C "$TEST_PROJECT" config core.hooksPath)

    [ "$initial_links" = "$final_links" ]
    [ "$initial_gitignore" = "$final_gitignore" ]
    [ "$initial_hooks_path" = "$final_hooks_path" ]
}

@test "harness-link.sh: --with-statusline installs .claude/statusline.sh and wires statusLine in settings.json" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Installed statusline" ]]

    [ -x "$TEST_PROJECT/.claude/statusline.sh" ]
    command=$(python3 -c "import json; print(json.load(open('$TEST_PROJECT/.claude/settings.json'))['statusLine']['command'])")
    [ "$command" = "$TEST_PROJECT/.claude/statusline.sh" ]
}

@test "harness-link.sh: without --with-statusline, no statusline files are installed" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none

    [ ! -e "$TEST_PROJECT/.claude/statusline.sh" ]
    [ ! -e "$TEST_PROJECT/.claude/settings.json" ]
}

@test "harness-link.sh: --with-statusline skips (does not overwrite) an existing statusLine in settings.json" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.claude"
    cat > "$TEST_PROJECT/.claude/settings.json" <<'JSON'
{"statusLine": {"type": "command", "command": "my-own-statusline.sh"}}
JSON

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a statusLine configured" ]]

    command=$(python3 -c "import json; print(json.load(open('$TEST_PROJECT/.claude/settings.json'))['statusLine']['command'])")
    [ "$command" = "my-own-statusline.sh" ]
    [ ! -e "$TEST_PROJECT/.claude/statusline.sh" ]
}

@test "harness-link.sh: statusline install is piped session JSON and prints a status line" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m init

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline

    run bash -c "echo '{\"model\":{\"display_name\":\"Sonnet 5\"},\"workspace\":{\"current_dir\":\"$TEST_PROJECT\"},\"context_window\":{\"used_percentage\":10}}' | '$TEST_PROJECT/.claude/statusline.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Sonnet 5" ]]
    [[ "$output" =~ "stage-only" ]]
}

# Regression test for a Copilot review finding on PR #281: an authority
# contract's "expires" field with no UTC offset in its ISO string
# (e.g. "2099-01-01T00:00:00", no trailing Z or +HH:MM) parses to a
# timezone-naive datetime, which used to raise TypeError comparing it
# against the timezone-aware "now" — crashing the whole statusline under
# set -e instead of just that one grant's expiry.
@test "harness-link.sh: statusline does not crash on a timezone-naive authority expiry" {
    git -C "$TEST_PROJECT" init --quiet
    git -C "$TEST_PROJECT" -c user.email=test@example.com -c user.name=Test commit --quiet --allow-empty -m init
    cat > "$TEST_PROJECT/.agentharness-authority.json" <<'JSON'
{"grants": [{"operations": ["push"], "expires": "2099-01-01T00:00:00"}]}
JSON

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline

    run bash -c "echo '{\"model\":{\"display_name\":\"Sonnet 5\"},\"workspace\":{\"current_dir\":\"$TEST_PROJECT\"},\"context_window\":{\"used_percentage\":10}}' | '$TEST_PROJECT/.claude/statusline.sh'"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "scoped(1" ]]
}

@test "harness-link.sh: doctor reports statusline health when --with-statusline was used" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "statusline (Claude Code): .claude/statusline.sh present" ]]
}

@test "harness-link.sh: uninstall removes statusline.sh and its statusLine entry, ownership-guarded" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline
    [ -f "$TEST_PROJECT/.claude/statusline.sh" ]

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Removed .claude/statusline.sh" ]]
    [ ! -e "$TEST_PROJECT/.claude/statusline.sh" ]
    run python3 -c "import json,sys; sys.exit(1 if 'statusLine' in json.load(open('$TEST_PROJECT/.claude/settings.json')) else 0)"
    [ "$status" -eq 0 ]
}

@test "harness-link.sh: uninstall leaves statusline.sh untouched if settings.json was repointed elsewhere" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline
    python3 -c "
import json
path = '$TEST_PROJECT/.claude/settings.json'
data = json.load(open(path))
data['statusLine']['command'] = 'something-else.sh'
json.dump(data, open(path, 'w'))
"

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "no longer points at the agentharness script" ]]
    [ -f "$TEST_PROJECT/.claude/statusline.sh" ]
}

# Codex/Gemini statusline tests (issues #274/#275): --with-statusline
# always installs the Claude Code statusline (it's this harness's native
# client, not gated by --client), but Codex/Gemini config is only touched
# when that client is actually selected via --client.

@test "harness-link.sh: --with-statusline with --client codex installs tui.status_line, not gemini" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex --with-statusline
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Installed Codex statusline" ]]

    items=$(python3 -c "import tomllib; print(tomllib.load(open('$TEST_PROJECT/.codex/config.toml','rb'))['tui']['status_line'])")
    [[ "$items" =~ "current-dir" ]]
    [ ! -e "$TEST_PROJECT/.gemini/settings.json" ]
}

@test "harness-link.sh: --with-statusline with --client gemini installs ui.footer.items, not codex" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client gemini --with-statusline
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Installed Gemini statusline" ]]

    items=$(python3 -c "import json; print(json.load(open('$TEST_PROJECT/.gemini/settings.json'))['ui']['footer']['items'])")
    [[ "$items" =~ "context-used" ]]
    [ ! -e "$TEST_PROJECT/.codex/config.toml" ]
}

@test "harness-link.sh: --with-statusline with --client none installs neither Codex nor Gemini config" {
    git -C "$TEST_PROJECT" init --quiet

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client none --with-statusline
    [ "$status" -eq 0 ]
    [ -x "$TEST_PROJECT/.claude/statusline.sh" ]
    [ ! -e "$TEST_PROJECT/.codex/config.toml" ]
    [ ! -e "$TEST_PROJECT/.gemini/settings.json" ]
}

@test "harness-link.sh: Codex statusline install merges into an existing config.toml without disturbing other keys" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.codex"
    cat > "$TEST_PROJECT/.codex/config.toml" <<'TOML'
model = "gpt-5.1-codex"

[tui]
notify = true

[sandbox]
mode = "workspace-write"
TOML

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex --with-statusline
    [ "$status" -eq 0 ]

    run python3 -c "
import tomllib
data = tomllib.load(open('$TEST_PROJECT/.codex/config.toml', 'rb'))
assert data['model'] == 'gpt-5.1-codex'
assert data['tui']['notify'] is True
assert data['sandbox']['mode'] == 'workspace-write'
assert 'status_line' in data['tui']
"
    [ "$status" -eq 0 ]
}

@test "harness-link.sh: Gemini statusline install merges into existing settings.json without disturbing other keys" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.gemini"
    cat > "$TEST_PROJECT/.gemini/settings.json" <<'JSON'
{"ui": {"theme": "dark", "footer": {"hideCWD": true}}, "model": "gemini-3-pro"}
JSON

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client gemini --with-statusline
    [ "$status" -eq 0 ]

    run python3 -c "
import json
data = json.load(open('$TEST_PROJECT/.gemini/settings.json'))
assert data['ui']['theme'] == 'dark'
assert data['ui']['footer']['hideCWD'] is True
assert data['model'] == 'gemini-3-pro'
assert 'items' in data['ui']['footer']
"
    [ "$status" -eq 0 ]
}

@test "harness-link.sh: Codex/Gemini statusline install skips (does not overwrite) a different existing value" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.codex" "$TEST_PROJECT/.gemini"
    printf '[tui]\nstatus_line = ["model", "current-dir"]\n' > "$TEST_PROJECT/.codex/config.toml"
    printf '{"ui": {"footer": {"items": ["model-name"]}}}\n' > "$TEST_PROJECT/.gemini/settings.json"

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex,gemini --with-statusline
    [ "$status" -eq 0 ]
    [[ "$output" =~ "already has a different tui.status_line configured" ]]
    [[ "$output" =~ "already has a different ui.footer.items configured" ]]

    codex_items=$(python3 -c "import tomllib; print(tomllib.load(open('$TEST_PROJECT/.codex/config.toml','rb'))['tui']['status_line'])")
    [ "$codex_items" = "['model', 'current-dir']" ]
    gemini_items=$(python3 -c "import json; print(json.load(open('$TEST_PROJECT/.gemini/settings.json'))['ui']['footer']['items'])")
    [ "$gemini_items" = "['model-name']" ]
}

@test "harness-link.sh: doctor reports Codex and Gemini statusline health" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex,gemini --with-statusline

    run bash "$SCRIPT" doctor "$TEST_PROJECT"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "statusline (Codex): tui.status_line present" ]]
    [[ "$output" =~ "statusline (Gemini): ui.footer.items present" ]]
}

@test "harness-link.sh: uninstall removes tui.status_line and ui.footer.items, ownership-guarded, leaving sibling keys" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.codex" "$TEST_PROJECT/.gemini"
    printf '[sandbox]\nmode = "workspace-write"\n' > "$TEST_PROJECT/.codex/config.toml"
    printf '{"model": "gemini-3-pro"}\n' > "$TEST_PROJECT/.gemini/settings.json"

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex,gemini --with-statusline

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Removed tui.status_line from .codex/config.toml" ]]
    [[ "$output" =~ "Removed ui.footer.items from .gemini/settings.json" ]]

    run python3 -c "
import tomllib
data = tomllib.load(open('$TEST_PROJECT/.codex/config.toml', 'rb'))
assert data['sandbox']['mode'] == 'workspace-write'
assert 'status_line' not in data.get('tui', {})
"
    [ "$status" -eq 0 ]
    run python3 -c "
import json
data = json.load(open('$TEST_PROJECT/.gemini/settings.json'))
assert data['model'] == 'gemini-3-pro'
assert 'footer' not in data.get('ui', {})
"
    [ "$status" -eq 0 ]
}

@test "harness-link.sh: uninstall leaves Codex/Gemini statusline untouched if changed since install" {
    git -C "$TEST_PROJECT" init --quiet

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex,gemini --with-statusline
    python3 -c "
path = '$TEST_PROJECT/.codex/config.toml'
text = open(path).read().replace('current-dir', 'hostname')
open(path, 'w').write(text)
"
    python3 -c "
import json
path = '$TEST_PROJECT/.gemini/settings.json'
data = json.load(open(path))
data['ui']['footer']['items'].append('hostname')
json.dump(data, open(path, 'w'))
"

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "tui.status_line no longer matches" ]]
    [[ "$output" =~ "ui.footer.items no longer matches" ]]

    codex_has_status_line=$(python3 -c "import tomllib; print('status_line' in tomllib.load(open('$TEST_PROJECT/.codex/config.toml','rb'))['tui'])")
    [ "$codex_has_status_line" = "True" ]
    gemini_has_items=$(python3 -c "import json; print('items' in json.load(open('$TEST_PROJECT/.gemini/settings.json'))['ui']['footer'])")
    [ "$gemini_has_items" = "True" ]
}

# Regression tests for Copilot review findings on PR #281: the [tui]
# header detection/removal used an exact `line.strip() == "[tui]"` (or
# equivalent) match, which misses a header with a trailing inline TOML
# comment — on install that silently appended a *second* [tui] header
# (invalid TOML, since a table can't be defined twice), and on uninstall
# it left the status_line line behind instead of removing it.

@test "harness-link.sh: Codex install does not duplicate [tui] when the header has a trailing comment" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.codex"
    printf '[tui] # my personal tui settings\nnotify = true\n' > "$TEST_PROJECT/.codex/config.toml"

    run bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex --with-statusline
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Installed Codex statusline" ]]

    run python3 -c "
import tomllib
data = tomllib.load(open('$TEST_PROJECT/.codex/config.toml', 'rb'))
assert data['tui']['notify'] is True
assert 'status_line' in data['tui']
"
    [ "$status" -eq 0 ]
    # Exactly one [tui] header — a second one would make this invalid TOML,
    # which the tomllib.load() call above would already have caught, but
    # assert the header count explicitly too.
    header_count=$(grep -c '^\[tui\]' "$TEST_PROJECT/.codex/config.toml")
    [ "$header_count" -eq 1 ]
}

@test "harness-link.sh: uninstall removes tui.status_line even with a trailing inline comment on that line" {
    git -C "$TEST_PROJECT" init --quiet
    mkdir -p "$TEST_PROJECT/.codex"
    printf '[tui]\nstatus_line = ["model-with-reasoning", "approval-mode", "context-used", "current-dir"] # installed by agentharness\n' > "$TEST_PROJECT/.codex/config.toml"

    bash "$SCRIPT" "$TEST_PROJECT" --skills none --client codex --with-statusline

    run bash "$SCRIPT" uninstall "$TEST_PROJECT" --yes
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Removed tui.status_line from .codex/config.toml" ]]

    run python3 -c "
import tomllib
data = tomllib.load(open('$TEST_PROJECT/.codex/config.toml', 'rb'))
assert 'status_line' not in data.get('tui', {})
"
    [ "$status" -eq 0 ]
}
