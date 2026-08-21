#!/usr/bin/env bash
# ============================================================================
# harness-session-start.sh — dirty-tree worktree reminder for consumer repos
# ============================================================================
#
# Prints a warning (exits 0 unless argv is invalid — never blocks a
# non-erroring call) when the current working tree is dirty
# (`git status --porcelain` non-empty) and the caller isn't already inside
# a git worktree. Does not evaluate branch naming or relatedness — a
# clean tree on an unrelated branch is not detected here, only the dirty-
# tree half of the `branching` skill's rule. Closes the gap that rule
# otherwise leaves for a consumer that hasn't wired up full hook
# integration (issue #249, item 7): without this, there's no session-start
# signal at all, only a rule buried in a skill doc an agent may or may not
# re-read every turn.
#
# This is guidance-that-prints, not enforcement — deliberately not a
# PreToolUse/pre-commit hook (see issue #249's item 3, declined: the gap
# #249 actually reported was a skipped mandatory rule despite it already
# being documented and prescriptive, not a missing enforcement layer; a new
# hook adds maintenance surface — threshold tuning, false positives on a
# legitimately dirty checkout — to re-solve a problem review already
# catches). No dependency beyond git; no state, no config, no new
# subsystem.
#
# Usage:
#   tools/harness-session-start.sh [--base <ref>]
#
# --base defaults to origin/main. Run this from any consumer project (it
# only ever inspects the current git working tree) at the start of an
# agent session — wire it into AGENTS.md's "start of every session" step,
# or call it manually.
# ============================================================================
set -euo pipefail

base_ref="origin/main"
while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            if [ -z "${2:-}" ]; then
                echo "Error: --base requires a value." >&2
                exit 1
            fi
            base_ref="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--base <ref>]"
            exit 0 ;;
        *)
            echo "Unexpected argument: $1" >&2
            exit 1 ;;
    esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # Not a git repo at all -- nothing to check, nothing to warn about.
    exit 0
fi

# Already inside a linked worktree (not the main checkout) -- the isolation
# this script nudges toward is already in place.
git_common_dir="$(git rev-parse --git-common-dir 2>/dev/null || true)"
git_dir="$(git rev-parse --git-dir 2>/dev/null || true)"
if [ -n "$git_common_dir" ] && [ "$git_common_dir" != "$git_dir" ]; then
    exit 0
fi

if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
    # Clean tree -- a plain `git checkout -b` from here is safe.
    exit 0
fi

current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"
suggested_dir=".worktrees/feature-<short-name>"

cat >&2 <<EOF
[harness-session-start] Working tree is dirty (branch: $current_branch).
  Starting new feature/fix work here risks mixing it with these unrelated
  changes -- the branching skill's own rule makes a worktree mandatory in
  this state, not a preference. Isolate before editing:

    git fetch origin
    git worktree add -b feature/<short-name> $suggested_dir $base_ref
    cd $suggested_dir

  (Not new work? A quick, unrelated edit on the current branch doesn't need
  this -- see the branching skill's own carve-outs.)
EOF
exit 0
