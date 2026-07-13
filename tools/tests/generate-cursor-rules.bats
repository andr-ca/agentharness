#!/usr/bin/env bats
#
# Tests for tools/generate-cursor-rules.sh: Cursor is the one platform
# with no confirmed Agent Skills (SKILL.md) support, so this generator's
# shape differs from AGENTS.md/GEMINI.md/Kilo's rules file — it produces
# one .mdc per skill (full body, description copied verbatim, no globs
# so activation is Agent-Requested) plus one always-on router file.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-cursor-rules.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-cursor-rules: produces one .mdc per skill plus the always-on router" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    [ -f "$BATS_TEST_TMPDIR/.cursor/rules/agentharness-router.mdc" ]
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        [ -f "$BATS_TEST_TMPDIR/.cursor/rules/$skill.mdc" ]
    done
}

@test "generate-cursor-rules: agentharness-router.mdc carries alwaysApply: true" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    grep -q "^alwaysApply: true$" "$BATS_TEST_TMPDIR/.cursor/rules/agentharness-router.mdc"
}

@test "generate-cursor-rules: each skill's .mdc description matches its source SKILL.md verbatim" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        skill_md="$skill_dir/SKILL.md"
        [ -f "$skill_md" ] || continue
        expected="$(grep -m1 '^description: ' "$skill_md" | sed 's/^description: //')"
        actual="$(grep -m1 '^description: ' "$BATS_TEST_TMPDIR/.cursor/rules/$skill.mdc" | sed -E 's/^description: "?//; s/"?$//')"
        [ "$actual" = "$expected" ]
    done
}

@test "generate-cursor-rules: skill .mdc files carry no globs — Agent-Requested activation, not Auto-Attached" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for skill_dir in "$HARNESS_ROOT"/.claude/skills/*/; do
        skill="$(basename "$skill_dir")"
        ! grep -q "^globs:" "$BATS_TEST_TMPDIR/.cursor/rules/$skill.mdc"
    done
}

@test "generate-cursor-rules: committed .cursor/rules/*.mdc match the generator's current output" {
    # Regression guard duplicating check_cursor_rules_sync() in
    # tools/verify-content-quality.py so a local 'bats' run alone catches
    # a stale commit too.
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.cursor/rules" "$HARNESS_ROOT/.cursor/rules"
}
