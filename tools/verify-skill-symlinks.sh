#!/usr/bin/env bash
# ============================================================================
# verify-skill-symlinks.sh — verify the .agents/skills/ and .qwen/skills/
# compatibility symlink farms stay 1:1 with .claude/skills/ (the real
# skill directories).
# ============================================================================
#
# .claude/skills/<name>/ holds the real skill (SKILL.md plus any bundled
# resources). Every non-Claude tool that speaks the Agent Skills standard
# (Codex CLI, GitHub Copilot, Gemini CLI, Kilo Code, OpenCode, ...) reads
# instead from .agents/skills/<name>, which this repo populates as a
# relative symlink back to ../../.claude/skills/<name>. Qwen Code doesn't
# speak that shared standard — it scans its own .qwen/skills/<name>
# instead (verified against the CLI's own bundled docs; see
# tools/generate-qwen-md.sh's header) — so this repo maintains a second,
# identically-shaped symlink farm there.
#
# Why this needs its own check: if a skill is added under .claude/skills/
# without its matching mirror symlink in either farm (or a symlink is
# left dangling, points somewhere unexpected, or a bundled-resource
# symlink inside a skill breaks), the affected tools silently stop
# seeing that skill while Claude Code still does. Worse, the generated
# skill index in AGENTS.md / .github/copilot-instructions.md / GEMINI.md
# / QWEN.md is built from .claude/skills/, so it would still list the
# skill — making the drift invisible without a dedicated invariant check.
#
# Verifies, for a given repo root (default: this script's own repo) and
# each mirror directory (.agents/skills, .qwen/skills):
#   1. every .claude/skills/<name>/ containing a SKILL.md has a matching
#      <mirror>/<name> that is a symlink resolving to it;
#   2. every <mirror>/<name> is a symlink, resolves (not dangling), and
#      maps back to a real .claude/skills/<name> (no orphan/foreign
#      targets);
#   3. every bundled-resource symlink inside .claude/skills/** resolves
#      (e.g. agentic-loops/agent_loop.py -> ../../../patterns/...) —
#      checked once, not per mirror, since it's about .claude/skills/
#      itself.
#
# Usage: bash tools/verify-skill-symlinks.sh [repo-root]
# Exit codes: 0 = all good, 1 = a mismatch / dangling / orphan symlink.
# ============================================================================
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
claude_skills="$REPO_ROOT/.claude/skills"
MIRROR_SKILL_SUBDIRS=(".agents/skills" ".qwen/skills")

fail=0
note_fail() {
    echo "  ✗ $1" >&2
    fail=1
}

# Canonicalize a directory path (resolve symlinks) portably — macOS
# readlink has no -f, so use a cd + pwd -P subshell instead. `|| true`
# guarantees it never returns non-zero (so it's safe under `set -e` in any
# context, not just the string comparisons below): a target that isn't a
# directory yields an empty string, which the callers already treat as a
# mismatch/failure.
canonical_dir() { (cd "$1" 2>/dev/null && pwd -P) || true; }

if [ ! -d "$claude_skills" ]; then
    echo "ERROR: $claude_skills not found" >&2
    exit 1
fi

# verify_mirror MIRROR_SUBDIR — runs checks 1 and 2 against one mirror
# farm (e.g. ".agents/skills"), against the shared $claude_skills.
verify_mirror() {
    local mirror_subdir="$1"
    local mirror_skills="$REPO_ROOT/$mirror_subdir"

    if [ ! -d "$mirror_skills" ]; then
        echo "  ✗ $mirror_subdir/ is missing entirely — no skill is visible to" >&2
        echo "    tools that read $mirror_subdir/." >&2
        fail=1
        return
    fi

    echo "Verifying .claude/skills/ <-> $mirror_subdir/ symlinks..."

    # 1. Every real skill has a resolving symlink pointing at it.
    for skill_md in "$claude_skills"/*/SKILL.md; do
        [ -e "$skill_md" ] || continue   # skip the literal glob when no matches
        local name link
        name="$(basename "$(dirname "$skill_md")")"
        link="$mirror_skills/$name"

        if [ ! -L "$link" ]; then
            if [ -e "$link" ]; then
                note_fail "$name: $mirror_subdir/$name exists but is not a symlink"
            else
                note_fail "$name: .claude/skills/$name/SKILL.md has no $mirror_subdir/$name symlink"
            fi
            continue
        fi
        if [ ! -e "$link" ]; then
            note_fail "$name: $mirror_subdir/$name is a dangling symlink (target '$(readlink "$link")' does not resolve)"
            continue
        fi
        if [ "$(canonical_dir "$link")" != "$(canonical_dir "$claude_skills/$name")" ]; then
            note_fail "$name: $mirror_subdir/$name resolves to '$(canonical_dir "$link")', expected '$(canonical_dir "$claude_skills/$name")'"
            continue
        fi
        echo "  ✓ $name"
    done

    # 2. No orphan symlinks: every mirror entry maps back to a real skill.
    for link in "$mirror_skills"/*; do
        [ -e "$link" ] || [ -L "$link" ] || continue   # skip literal glob / nothing there
        local name
        name="$(basename "$link")"
        if [ ! -L "$link" ]; then
            note_fail "$name: $mirror_subdir/$name is not a symlink (should point at ../../.claude/skills/$name)"
            continue
        fi
        if [ ! -e "$claude_skills/$name/SKILL.md" ]; then
            note_fail "$name: $mirror_subdir/$name is an orphan — no .claude/skills/$name/SKILL.md behind it"
        fi
    done
}

for mirror_subdir in "${MIRROR_SKILL_SUBDIRS[@]}"; do
    verify_mirror "$mirror_subdir"
done

# 3. Every bundled-resource symlink inside a real skill resolves.
while IFS= read -r -d '' l; do
    if [ ! -e "$l" ]; then
        note_fail "bundled resource ${l#"$REPO_ROOT"/} is a dangling symlink (target '$(readlink "$l")')"
    fi
done < <(find "$claude_skills" -type l -print0)

if [ "$fail" -ne 0 ]; then
    echo "Skill symlink verification FAILED." >&2
    exit 1
fi
echo "All skill symlinks resolve 1:1 with .claude/skills/."
