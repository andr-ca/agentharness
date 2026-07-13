#!/usr/bin/env bats
#
# Tests for tools/generate-gemini-md.sh: GEMINI.md is routing rules only,
# from CLAUDE.md — mirrors generate-agents-md.bats's assertions exactly,
# since GEMINI.md follows the same shape (skill index, not skill bodies).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-gemini-md.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-gemini-md: skill index lists every installed skill's name and description, not its body" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [[ "$output" =~ ".agents/skills/$skill/SKILL.md" ]]
    done
    [[ "$output" != *"Before you commit"* ]]
    [[ "$output" =~ "atomic commits, message format" ]]
}

@test "generate-gemini-md: documents Gemini CLI's activate_skill mechanism and Antigravity's precedence" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"loaded on demand from"*".agents/skills/"* ]]
    [[ "$output" == *"activate_skill"* ]]
    [[ "$output" == *"Antigravity"* ]]
    [[ "$output" == *"precedence over"*"AGENTS.md"* ]]
}

@test "generate-gemini-md: path resolution — every referenced .agents/skills/*/SKILL.md path exists on disk" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [ -e "$HARNESS_ROOT/.agents/skills/$skill/SKILL.md" ]
    done
}

@test "generate-gemini-md: --output writes to a file instead of stdout" {
    out="$BATS_TEST_TMPDIR/GEMINI.md"
    run bash "$SCRIPT" --output "$out"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$out" ]
    grep -q "committing/SKILL.md" "$out"
}

@test "generate-gemini-md: committed GEMINI.md at repo root matches the generator's current output" {
    # Regression guard duplicating check_gemini_md_sync() in
    # tools/verify-content-quality.py so a local 'bats' run alone catches
    # a stale commit too.
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    committed="$(cat "$HARNESS_ROOT/GEMINI.md")"
    [ "$output" = "$committed" ]
}
