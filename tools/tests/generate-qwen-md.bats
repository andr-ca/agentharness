#!/usr/bin/env bats
#
# Tests for tools/generate-qwen-md.sh: QWEN.md is routing rules only,
# from CLAUDE.md — mirrors generate-gemini-md.bats's assertions, except
# the skill index points at .qwen/skills/ (Qwen Code's own discovery
# directory), not .agents/skills/ — see the generator's header for why.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-qwen-md.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-qwen-md: skill index lists every installed skill's name and description, not its body" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [[ "$output" =~ ".qwen/skills/$skill/SKILL.md" ]]
    done
    [[ "$output" != *"Before you commit"* ]]
    [[ "$output" =~ "atomic commits, message format" ]]
}

@test "generate-qwen-md: documents Qwen Code's own .qwen/skills/ discovery mechanism, not .agents/skills/" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"loaded on demand from"*".qwen/skills/"* ]]
    [[ "$output" != *".agents/skills/"* ]]
    [[ "$output" == *"/memory refresh"* ]]
}

@test "generate-qwen-md: path resolution — every referenced .qwen/skills/*/SKILL.md path exists on disk" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [ -e "$HARNESS_ROOT/.qwen/skills/$skill/SKILL.md" ]
    done
}

@test "generate-qwen-md: --output writes to a file instead of stdout" {
    out="$BATS_TEST_TMPDIR/QWEN.md"
    run bash "$SCRIPT" --output "$out"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$out" ]
    grep -q "committing/SKILL.md" "$out"
}

@test "generate-qwen-md: committed QWEN.md at repo root matches the generator's current output" {
    # Regression guard duplicating check_qwen_md_sync() in
    # tools/verify-content-quality.py so a local 'bats' run alone catches
    # a stale commit too.
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    committed="$(cat "$HARNESS_ROOT/QWEN.md")"
    [ "$output" = "$committed" ]
}
