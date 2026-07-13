#!/usr/bin/env bats
#
# Tests for tools/generate-copilot-agents.sh: ports .claude/agents/*.md
# subagent definitions to GitHub Copilot's own custom-agent format
# (.github/agents/*.agent.md — genuine sub-agent delegation with an
# isolated context, confirmed against docs.github.com after an earlier
# research pass wrongly classified Copilot as persona-only). Tool and
# target/disable-model-invocation/user-invocable scoping are
# deliberately not translated (see the generator's own header comment).

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../generate-copilot-agents.sh"
    HARNESS_ROOT="$BATS_TEST_DIRNAME/../.."
}

@test "generate-copilot-agents: produces one .agent.md per .claude/agents/*.md" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        [ -f "$BATS_TEST_TMPDIR/.github/agents/$agent.agent.md" ]
    done
}

@test "generate-copilot-agents: every generated file's frontmatter is valid YAML with name/description/model matching the source" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$HARNESS_ROOT"/.claude/agents/*.md; do
        [ -f "$agent_md" ] || continue
        agent="$(basename "$agent_md" .md)"
        run python3 -c "
import yaml
src_fm = yaml.safe_load(open('$agent_md').read().split('---')[1])
out_fm = yaml.safe_load(open('$BATS_TEST_TMPDIR/.github/agents/$agent.agent.md').read().split('---')[1])
assert out_fm['name'] == src_fm['name']
assert out_fm['description'] == src_fm['description']
assert out_fm['model'] == src_fm['model']
"
        [ "$status" -eq 0 ]
    done
}

@test "generate-copilot-agents: does not port tools/target/disable-model-invocation/user-invocable" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    for agent_md in "$BATS_TEST_TMPDIR"/.github/agents/*.agent.md; do
        ! grep -q "^tools\|^target\|^disable-model-invocation\|^user-invocable" "$agent_md"
    done
}

@test "generate-copilot-agents: committed .github/agents/*.agent.md match the generator's current output" {
    bash "$SCRIPT" "$HARNESS_ROOT" --output-dir "$BATS_TEST_TMPDIR"
    diff -r "$BATS_TEST_TMPDIR/.github/agents" "$HARNESS_ROOT/.github/agents"
}
