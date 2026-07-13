#!/usr/bin/env bats
#
# Tests for tools/generate-kilo-rules.sh: .kilo/rules/agentharness.md is
# routing rules only, from CLAUDE.md — mirrors generate-agents-md.bats's
# assertions exactly, since it follows the same shape (skill index, not
# skill bodies).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-kilo-rules.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-kilo-rules: skill index lists every installed skill's name and description, not its body" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [[ "$output" =~ ".agents/skills/$skill/SKILL.md" ]]
    done
    [[ "$output" != *"Before you commit"* ]]
    [[ "$output" =~ "atomic commits, message format" ]]
}

@test "generate-kilo-rules: documents Kilo's auto-discovered .kilo/rules/ directory" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"loaded on demand from"*".agents/skills/"* ]]
    [[ "$output" == *"auto-discovers every file placed under"*".kilo/rules/"* ]]
    [[ "$output" == *"no"*"kilo.jsonc"*"entry is required"* ]]
}

@test "generate-kilo-rules: path resolution — every referenced .agents/skills/*/SKILL.md path exists on disk" {
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [ -e "$HARNESS_ROOT/.agents/skills/$skill/SKILL.md" ]
    done
}

@test "generate-kilo-rules: --output writes to a file instead of stdout" {
    out="$BATS_TEST_TMPDIR/agentharness.md"
    run bash "$SCRIPT" --output "$out"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ -f "$out" ]
    grep -q "committing/SKILL.md" "$out"
}

@test "generate-kilo-rules: committed .kilo/rules/agentharness.md matches the generator's current output" {
    # Regression guard duplicating check_kilo_rules_sync() in
    # tools/verify-content-quality.py so a local 'bats' run alone catches
    # a stale commit too.
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    committed="$(cat "$HARNESS_ROOT/.kilo/rules/agentharness.md")"
    [ "$output" = "$committed" ]
}
