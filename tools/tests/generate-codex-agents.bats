#!/usr/bin/env bats
#
# Tests for tools/generate-codex-agents.sh: ports .claude/agents/*.md
# subagent definitions to Codex CLI's TOML format. Tool/permission
# scoping is deliberately not translated (see the generator's own header
# comment) — these tests only check name/description/model/body survive
# the port and that the TOML is actually valid, not just string-matched
# (learned from this session's yaml_dquote_escape bug: a naive substring
# comparison can pass while the escaping is subtly wrong).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-codex-agents.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-codex-agents: produces one .toml per .claude/agents/*.md" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        [ -f "$BATS_TEST_TMPDIR/.codex/agents/$agent.toml" ]
    done
}

@test "generate-codex-agents: every generated file is valid TOML with name/description/model matching the source" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        run python3 -c "
import tomllib, yaml
with open('$BATS_TEST_TMPDIR/.codex/agents/$agent.toml', 'rb') as f:
    toml_data = tomllib.load(f)
src_fm = yaml.safe_load(open('$agent_md').read().split('---')[1])
assert toml_data['name'] == src_fm['name']
assert toml_data['description'] == src_fm['description']
assert toml_data['model'] == src_fm['model']
assert 'developer_instructions' in toml_data
"
        [ "$status" -eq 0 ]
    done
}

@test "generate-codex-agents: does not port the tools field" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for toml in "$BATS_TEST_TMPDIR"/.codex/agents/*.toml; do
        ! grep -q "^tools" "$toml"
    done
}

@test "generate-codex-agents: committed .codex/agents/*.toml match the generator's current output" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.codex/agents" "$HARNESS_ROOT/.codex/agents"
}
