#!/usr/bin/env bats
#
# Tests for tools/generate-qwen-agents.sh: ports .claude/agents/*.md
# subagent definitions to Qwen Code's own custom-subagent format
# (.qwen/agents/*.md — genuine sub-agent delegation with its own
# separate context, confirmed against the CLI's own bundled docs,
# docs/features/sub-agents.md, installed 0.21.5). Tool/permission
# scoping is deliberately not translated (see the generator's own
# header comment) — same reasoning as every other agent-porting
# generator here.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-qwen-agents.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-qwen-agents: produces one .md per .claude/agents/*.md" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        [ -f "$BATS_TEST_TMPDIR/.qwen/agents/$agent.md" ]
    done
}

@test "generate-qwen-agents: every generated file's frontmatter is valid YAML with name/description/model matching the source" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        run python3 -c "
import yaml
src_fm = yaml.safe_load(open('$agent_md').read().split('---')[1])
out_fm = yaml.safe_load(open('$BATS_TEST_TMPDIR/.qwen/agents/$agent.md').read().split('---')[1])
assert out_fm['name'] == src_fm['name']
assert out_fm['description'] == src_fm['description']
assert out_fm['model'] == src_fm['model']
"
        [ "$status" -eq 0 ]
    done
}

@test "generate-qwen-agents: does not port tools/disallowedTools/approvalMode" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$BATS_TEST_TMPDIR"/.qwen/agents/*.md; do
        ! grep -q "^tools\|^disallowedTools\|^approvalMode" "$agent_md"
    done
}

@test "generate-qwen-agents: committed .qwen/agents/*.md match the generator's current output" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.qwen/agents" "$HARNESS_ROOT/.qwen/agents"
}
