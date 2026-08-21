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
