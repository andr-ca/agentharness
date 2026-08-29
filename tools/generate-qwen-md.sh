#!/usr/bin/env bash
# ============================================================================
# generate-qwen-md.sh — build a QWEN.md (Qwen Code's default context file)
# from the same CLAUDE.md this repo's own agents read.
# ============================================================================
#
# Qwen Code's context file defaults to QWEN.md (configurable via the
# `context.fileName` setting, but QWEN.md is what a project gets with no
# extra configuration — verified against the CLI's own bundled docs,
# `docs/configuration/settings.md`, at the currently-installed 0.21.5
# release: "context files (defaulting to QWEN.md but configurable via
# the context.fileName setting)"). It does NOT read AGENTS.md unless a
# consumer explicitly adds it to `context.fileName` in `.qwen/settings.json`
# — so unlike Codex/OpenCode/Zed, this repo can't lean on the shared
# AGENTS.md-family splice path here; QWEN.md needs its own generator,
# same as GEMINI.md.
#
# Qwen Code's Agent Skills support is also its own separate surface: it
# discovers skills from `.qwen/skills/` (project) and `~/.qwen/skills/`
# (personal), not `.agents/skills/` (confirmed from the same bundled
# docs, `docs/features/skills.md`) — so this generator's skill index
# points at `.qwen/skills/`, and harness-link.sh mirrors every installed
# skill there too, alongside `.claude/skills/` and `.agents/skills/`.
#
# QWEN.md therefore follows the exact same shape as GEMINI.md
# (tools/generate-gemini-md.sh): CLAUDE.md's routing prose plus a
# name+description skill index — never full skill bodies, which would
# defeat the point of on-demand loading.
#
# Live-verification status (2026-08-28): the facts above are confirmed
# from Qwen Code's own installed CLI docs (a primary, version-matched
# source), but NOT yet confirmed by watching a real agentic session load
# QWEN.md or invoke a skill from `.qwen/skills/` — the local Qwen OAuth
# free tier is discontinued and doing that live check would require
# opting into a paid provider, which wasn't authorized this round. See
# docs/CLIENT_COMPATIBILITY.md's Qwen Code rows for the same caveat;
# don't claim "N clients supported" as fully live-verified for qwen
# until that session happens.
#
# Usage:
#   tools/generate-qwen-md.sh [harness-dir] [--output <path>]
#
# harness-dir defaults to this script's own repo root. Without --output,
# writes to stdout.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=./setup/harness-link.sh
source "$SCRIPT_DIR/setup/harness-link.sh"
# shellcheck source=./lib/adapter-common.sh
source "$SCRIPT_DIR/lib/adapter-common.sh"

harness_dir=""
# shellcheck disable=SC2034  # used by write_generated_content() in adapter-common.sh
output=""
parse_common_adapter_args "$@"

claude_md="$harness_dir/CLAUDE.md"
skills_dir="$(resolve_target_skills_dir "$harness_dir" "${output:+$(dirname "$output")}" ".qwen/skills")"

if [ ! -f "$claude_md" ]; then
    echo "Error: $claude_md not found." >&2
    exit 1
fi

generate() {
    cat <<'HEADER'
# QWEN.md

Generated from this repo's own `CLAUDE.md` by `tools/generate-qwen-md.sh`
(https://github.com/andr-ca/agentharness) — do not hand-edit; regenerate
instead (`tools/generate-qwen-md.sh --output QWEN.md`). A CI check keeps
this file in sync with its source (see `.github/workflows/ci.yml`'s
`content-quality` job).

This file covers repo-wide routing rules only. Skills are loaded on
demand from `.qwen/skills/` — Qwen Code's own Agent Skills mechanism
scans `.qwen/skills/` (project) and `~/.qwen/skills/` (personal) for
`SKILL.md` files and lets the model invoke one by name once its
description matches the task at hand. The index below exists so the
model has something to match against; it is not a substitute for
reading the matched `SKILL.md` itself.

Qwen Code also supports `/memory show` (inspect the concatenated
context) and `/memory refresh` (force a re-scan) if this file changes
mid-session.

---

HEADER

    # Reproduced content: CLAUDE.md doesn't itself claim a specific
    # skill-loading mechanism (that's client-specific behavior, not
    # something asserted in this file's text). Headings demoted so its
    # own "# agentharness – Agent Router" H1 doesn't collide with this
    # file's H1.
    demote_headings < "$claude_md"

    echo
    echo "---"
    echo
    render_skill_index "$harness_dir" "$skills_dir" ".qwen/skills"
}

generate | write_generated_content
