#!/usr/bin/env bats
#
# Tests for `harness-link.sh generate-clients` (P1-01, first increment) —
# runs this repo's client-adapter generators into a consumer project so a
# single command produces the router/instruction files, instead of the
# per-generator manual steps in docs/INTEGRATION.md.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../setup/harness-link.sh"
    TARGET=$(mktemp -d)
}

teardown() {
    rm -rf "$TARGET"
}

@test "generate-clients: --client all writes every adapter" {
    run bash "$SCRIPT" generate-clients "$TARGET"
    [ "$status" -eq 0 ]
    [ -f "$TARGET/AGENTS.md" ]
    [ -f "$TARGET/GEMINI.md" ]
    [ -f "$TARGET/.github/copilot-instructions.md" ]
    [ -f "$TARGET/.github/instructions/python.instructions.md" ]
    [ -f "$TARGET/.cursor/rules/agentharness-router.mdc" ]
    [ -f "$TARGET/.kilo/rules/agentharness.md" ]
    [ -f "$TARGET/QWEN.md" ]
}

@test "generate-clients: --client qwen writes only QWEN.md" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client qwen
    [ "$status" -eq 0 ]
    [ -f "$TARGET/QWEN.md" ]
    [ ! -f "$TARGET/GEMINI.md" ]
    [ ! -f "$TARGET/AGENTS.md" ]
    grep -q "loaded on demand from \`.qwen/skills/\`" "$TARGET/QWEN.md"
}

@test "generate-clients: a comma-separated subset writes only those clients" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client copilot,cursor
    [ "$status" -eq 0 ]
    [ -f "$TARGET/.github/copilot-instructions.md" ]
    [ -f "$TARGET/.cursor/rules/agentharness-router.mdc" ]
    [ ! -f "$TARGET/AGENTS.md" ]
    [ ! -f "$TARGET/GEMINI.md" ]
    [ ! -e "$TARGET/.kilo" ]
}

@test "generate-clients: single --client codex writes AGENTS.md only" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client codex
    [ "$status" -eq 0 ]
    [ -f "$TARGET/AGENTS.md" ]
    [ ! -f "$TARGET/GEMINI.md" ]
}

@test "generate-clients: generated AGENTS.md is non-empty and names the router" {
    bash "$SCRIPT" generate-clients "$TARGET" --client codex
    [ -s "$TARGET/AGENTS.md" ]
    grep -q "agentharness" "$TARGET/AGENTS.md"
}

@test "generate-clients: an unknown client is a clear error" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client bogus
    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown client 'bogus'" ]]
}

@test "generate-clients: --client with no value is a clear error, not a silent no-op" {
    run bash "$SCRIPT" generate-clients "$TARGET" --client
    [ "$status" -ne 0 ]
    [[ "$output" =~ "--client requires a value" ]]
}

@test "generate-clients: a non-directory target is a clear error" {
    run bash "$SCRIPT" generate-clients "$TARGET/does-not-exist"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "not a directory" ]]
}

@test "generate-clients: is idempotent — a second run reproduces identical files" {
    bash "$SCRIPT" generate-clients "$TARGET" --client copilot,cursor
    first="$(find "$TARGET" -type f -exec sha256sum {} + | sort -k2)"
    bash "$SCRIPT" generate-clients "$TARGET" --client copilot,cursor
    second="$(find "$TARGET" -type f -exec sha256sum {} + | sort -k2)"
    [ "$first" = "$second" ]
}

# ---------------------------------------------------------------------------
# F-03: Sentinel-file safety tests
# ---------------------------------------------------------------------------

@test "generate-clients: skips non-harness files without --force" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    # Create a non-harness AGENTS.md (no provenance header)
    echo "# My Custom AGENTS" > "$consumer/AGENTS.md"

    run bash "$SCRIPT" generate-clients "$consumer" --client codex

    # Verify file was not overwritten (check BEFORE rm -rf)
    local file_content
    file_content="$(cat "$consumer/AGENTS.md")"
    rm -rf "$consumer"

    # Must skip the file and report it, not silently overwrite
    [ "$status" -eq 0 ]
    [[ "$output" == *"SKIP"* ]]
    [[ "$output" != *"codex/opencode/zed"* ]]
    [[ "$file_content" == "# My Custom AGENTS" ]]
}

@test "generate-clients: --force overwrites non-harness file with warning" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    echo "# My Custom AGENTS" > "$consumer/AGENTS.md"

    run bash "$SCRIPT" generate-clients "$consumer" --client codex --force
    local generated_content
    generated_content="$(cat "$consumer/AGENTS.md" 2>/dev/null || echo '')"
    rm -rf "$consumer"

    # Should succeed, write, and warn
    [ "$status" -eq 0 ]
    [[ "$output" == *"WARNING"* ]]
    [[ "$generated_content" == *"Generated"* ]]
}

@test "generate-clients: --dry-run does not write files" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q

    run bash "$SCRIPT" generate-clients "$consumer" --client codex --dry-run

    # AGENTS.md must NOT have been created (check BEFORE rm -rf)
    local file_was_created=false
    [ -f "$consumer/AGENTS.md" ] && file_was_created=true
    rm -rf "$consumer"

    # dry-run mode reported
    [[ "$output" == *"dry-run"* ]]
    # File must not have been written
    [ "$file_was_created" = false ]
}

@test "generate-clients: overwrites harness-owned file without --force" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    # First run to create a harness-owned AGENTS.md
    bash "$SCRIPT" generate-clients "$consumer" --client codex

    # Second run should update silently (no SKIP, no WARNING)
    run bash "$SCRIPT" generate-clients "$consumer" --client codex
    rm -rf "$consumer"

    [ "$status" -eq 0 ]
    [[ "$output" != *"SKIP"* ]]
    [[ "$output" != *"WARNING"* ]]
    [[ "$output" == *"codex/opencode/zed"* ]]
}

# ---------------------------------------------------------------------------
# init's block-managed files, then a later standalone generate-clients call
# (issue #247 live-verification, real npm-registry repro on v0.8.0):
# _gc_is_harness_generated only recognizes the whole-file-generator's
# "Generated from/by" marker, not the `agentharness:begin` block-splice
# marker `init` writes for the 4 always-on files — so the documented
# init-then-generate-clients flow (also docs/COMPARE.md's own walkthrough)
# hit a false "not created by this harness" SKIP on a file the harness
# itself had just written moments earlier.
# ---------------------------------------------------------------------------

@test "generate-clients: recognizes a file init wrote as a block-managed surface, not foreign" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" init "$consumer" --mode copy --skills committing >/dev/null

    run bash "$SCRIPT" generate-clients "$consumer" --client copilot
    local content
    content="$(cat "$consumer/.github/copilot-instructions.md" 2>/dev/null || echo '')"
    rm -rf "$consumer"

    [ "$status" -eq 0 ]
    [[ "$output" != *"SKIP"* ]]
    [[ "$output" == *"copilot ->"* ]]
    [[ "$content" == *"Generated"* ]]
}

# ---------------------------------------------------------------------------
# Once generate-clients converts an init-written block-managed file into a
# whole-file surface (the test above), state must reflect the transition —
# otherwise doctor reports stale drift against a block marker the file no
# longer contains ("expected one managed block, found 0", issue #257).
# ---------------------------------------------------------------------------

@test "generate-clients: converting an init-written file to whole-file moves it from managed_blocks to overwritten_files" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" init "$consumer" --mode copy --skills committing >/dev/null
    bash "$SCRIPT" generate-clients "$consumer" --client copilot >/dev/null

    run python3 -c "
import json
d = json.load(open('$consumer/.agentharness-state.json'))
assert not any(b['file'] == '.github/copilot-instructions.md' for b in d['managed_blocks']), d['managed_blocks']
entry = next(o for o in d['overwritten_files'] if o['file'] == '.github/copilot-instructions.md')
assert entry['client'] == 'copilot', entry
assert entry['created_by_harness'] is True, entry
print('ok')
"
    local py_status="$status" py_output="$output"

    run bash "$SCRIPT" doctor "$consumer"
    local doctor_status="$status" doctor_output="$output"
    rm -rf "$consumer"

    [ "$py_status" -eq 0 ]
    [[ "$py_output" =~ "ok" ]]
    [ "$doctor_status" -eq 0 ]
    [[ "$doctor_output" != *"expected one managed block"* ]]
}

@test "generate-clients: does not relabel a non-harness-created managed block as created_by_harness=true (Copilot review, PR #261)" {
    # init spliced its block into a file the operator already owned
    # (created_by_harness=false) -- only reachable here via --force,
    # since _gc_is_state_managed_block requires created_by_harness=true
    # to let an unforced write through. That prior content is already
    # gone from disk by the time the transition helper runs, so there is
    # no way to construct the "backup" _restore_or_delete_entry() needs
    # for a non-harness-created overwritten_files entry -- recording it
    # as true instead would make a later uninstall delete a file this
    # harness never actually created. The transition must leave state
    # alone for this case rather than mislabel it.
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" init "$consumer" --mode copy --skills committing >/dev/null
    python3 -c "
import json
path = '$consumer/.agentharness-state.json'
d = json.load(open(path))
for b in d['managed_blocks']:
    if b['file'] == '.github/copilot-instructions.md':
        b['created_by_harness'] = False
json.dump(d, open(path, 'w'), indent=2)
"

    run bash "$SCRIPT" generate-clients "$consumer" --client copilot --force
    local gc_status="$status" gc_output="$output"

    run python3 -c "
import json
d = json.load(open('$consumer/.agentharness-state.json'))
entry = next(b for b in d['managed_blocks'] if b['file'] == '.github/copilot-instructions.md')
assert entry['created_by_harness'] is False, entry
assert not any(o['file'] == '.github/copilot-instructions.md' for o in d['overwritten_files']), d['overwritten_files']
print('ok')
"
    local py_status="$status" py_output="$output"
    rm -rf "$consumer"

    [ "$gc_status" -eq 0 ]
    [[ "$gc_output" == *"WARNING"* ]]
    [ "$py_status" -eq 0 ]
    [[ "$py_output" =~ "ok" ]]
}

@test "generate-clients --dry-run does not mutate managed_blocks/overwritten_files state" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" init "$consumer" --mode copy --skills committing >/dev/null
    local state_before
    state_before="$(cat "$consumer/.agentharness-state.json")"

    bash "$SCRIPT" generate-clients "$consumer" --client copilot --dry-run >/dev/null
    local state_after
    state_after="$(cat "$consumer/.agentharness-state.json")"
    rm -rf "$consumer"

    [ "$state_before" = "$state_after" ]
}

# ---------------------------------------------------------------------------
# copilot/cursor/kilo's provenance header wraps "Generated from/by ..."
# across two source lines; _gc_is_harness_generated()'s original same-line
# regex only matched AGENTS.md/GEMINI.md's single-line variant, so a
# second run of these three clients falsely treated their own prior output
# as foreign and required --force (Copilot review, PR #258).
# ---------------------------------------------------------------------------

@test "generate-clients: recognizes copilot's own multi-line provenance header on re-run" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" generate-clients "$consumer" --client copilot >/dev/null

    run bash "$SCRIPT" generate-clients "$consumer" --client copilot
    rm -rf "$consumer"

    [ "$status" -eq 0 ]
    [[ "$output" != *"SKIP"* ]]
    [[ "$output" == *"copilot ->"* ]]
}

# Unlike copilot/kilo's single output file, --client cursor writes one
# .mdc per skill, most of which are direct skill copies carrying no
# provenance marker of any kind — a re-run legitimately SKIPs on those
# (guarding against silently clobbering a hand-edited skill copy), so a
# full-command round-trip isn't a clean test of the router-file marker
# fix. Test _gc_is_harness_generated() directly against the router file
# instead, matching what the reviewer's finding actually concerned.
@test "generate-clients: recognizes cursor router's own multi-line provenance header" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" generate-clients "$consumer" --client cursor >/dev/null

    # shellcheck source=/dev/null
    source "$SCRIPT"
    run _gc_is_harness_generated "$consumer/.cursor/rules/agentharness-router.mdc"
    rm -rf "$consumer"

    [ "$status" -eq 0 ]
}

@test "generate-clients: recognizes kilo's own multi-line provenance header on re-run" {
    local consumer
    consumer="$(mktemp -d)"
    git -C "$consumer" init -q
    bash "$SCRIPT" generate-clients "$consumer" --client kilo >/dev/null

    run bash "$SCRIPT" generate-clients "$consumer" --client kilo
    rm -rf "$consumer"

    [ "$status" -eq 0 ]
    [[ "$output" != *"SKIP"* ]]
    [[ "$output" == *"kilo ->"* ]]
}
