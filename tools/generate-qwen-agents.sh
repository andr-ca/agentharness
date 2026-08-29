#!/usr/bin/env bash
# ============================================================================
# generate-qwen-agents.sh — port .claude/agents/*.md subagent
# definitions to Qwen Code's own custom-subagent format.
# ============================================================================
#
# Qwen Code supports real sub-agent delegation: a named subagent runs
# with its own separate conversation context, invoked automatically
# (task description matched against the subagent's own description) or
# explicitly. Config is Markdown with YAML frontmatter under
# .qwen/agents/ (project, highest precedence) or ~/.qwen/agents/
# (personal) — see the CLI's own bundled docs, docs/features/sub-agents.md
# (installed 0.21.5).
#
# Qwen Code's docs explicitly document accepting several Claude Code
# 2.1.168 frontmatter fields verbatim (permissionMode, maxTurns, color,
# mcpServers, hooks) so a CC agent file "dropped into .qwen/agents/"
# parses identically for those fields. That compatibility is about
# frontmatter *parsing*, not tool-name-vocabulary correctness, so this
# generator still does NOT port `tools`/`disallowedTools` — same
# reasoning as every other agent-porting generator here (see
# tools/lib/adapter-common.sh's agent_field() comment): Qwen's own tool
# names (`read_file`, `write_file`, `run_shell_command`, ...) don't
# match Claude Code's (`Read`, `Write`, `Bash`), so copying a `tools:`
# allowlist verbatim would silently leave the ported subagent with an
# empty, unusable toolset rather than an unported-but-harmless field.
#
# Usage:
#   tools/generate-qwen-agents.sh [harness-dir] [--output-dir <dir>]
#
# Writes one <output-dir>/.qwen/agents/<name>.md per
# .claude/agents/<name>.md this repo (or a consumer project) defines.
# harness-dir and output-dir both default to this script's own repo
# root, so running with no arguments regenerates this repo's own
# dogfooded files in place.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=./setup/harness-link.sh
source "$SCRIPT_DIR/setup/harness-link.sh"
# shellcheck source=./lib/adapter-common.sh
source "$SCRIPT_DIR/lib/adapter-common.sh"

harness_dir=""
output_dir=""
parse_multi_file_adapter_args "$@"

agents_dir="$harness_dir/.claude/agents"

generate_agent_md() {
    local agent_md="$1"
    local name description model
    name="$(agent_field "$agent_md" name)"
    description="$(yaml_dquote_escape "$(agent_field "$agent_md" description)")"
    model="$(agent_field "$agent_md" model)"

    cat <<EOF
---
name: $name
description: "$description"
model: $model
---

EOF
    cat <<HEADER
Generated from \`.claude/agents/$(basename "$agent_md")\` by
\`tools/generate-qwen-agents.sh\` (https://github.com/andr-ca/agentharness)
— do not hand-edit; regenerate
instead. Qwen Code's own \`tools\`/\`disallowedTools\`/\`approvalMode\`
fields are NOT ported (its tool-name vocabulary differs from Claude
Code's, so copying \`tools:\` verbatim would leave this subagent with
an empty, unusable toolset) — re-specify them here by hand if this
agent needs restricted tool access or a specific approval mode.

---

HEADER
    strip_frontmatter "$agent_md"
}

mkdir -p "$output_dir/.qwen/agents"

while IFS= read -r agent; do
    [ -z "$agent" ] && continue
    agent_md="$agents_dir/$agent.md"
    [ -f "$agent_md" ] || continue
    generate_agent_md "$agent_md" \
        | squeeze_blank_lines > "$output_dir/.qwen/agents/$agent.md"
done < <(list_available_agents "$harness_dir" | sort)
