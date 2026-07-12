#!/usr/bin/env bash
# ============================================================================
# harness-link.sh — one-command integration of agentharness into a project
# ============================================================================
#
# Usage:
#   harness-link.sh <target-project-dir> [--with-hook] [--force] [--skills skill1,skill2,...]
#
# What it does:
#   1. Symlinks .claude/skills/<name> from this harness into the target
#      project's .claude/skills/ (all skills by default, or a subset via
#      --skills)
#   2. Copies .github/.gitignore.template into the target's .gitignore,
#      merging with any existing .gitignore rather than overwriting it
#   3. With --with-hook: sets core.hooksPath in the target repo to this
#      harness's .github/hooks/ (requires the target to be a git repo,
#      including a linked worktree). This wires up both hooks git finds
#      there by filename:
#        - pre-commit: blocks direct commits to trunk branches
#        - pre-push: runs the test suite and blocks push below 80% coverage
#      Refuses to overwrite a core.hooksPath the target already has set to
#      something else — pass --force to replace it anyway.
#
# This script is idempotent — running it again re-syncs symlinks and skips
# gitignore lines that are already present.
# ============================================================================

set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
    cat <<EOF
Usage: $(basename "$0") <target-project-dir> [OPTIONS]

Options:
  --with-hook          Install the prevent-trunk-commit (pre-commit) and
                        test/coverage (pre-push) hooks in the target repo
                        via 'git config core.hooksPath'
  --force              With --with-hook, overwrite an existing
                        core.hooksPath that points somewhere else instead
                        of refusing
  --skills a,b,c        Comma-separated list of skills to link (default: all)
  -h, --help            Show this help

Example:
  $(basename "$0") ~/my-project --with-hook
  $(basename "$0") ~/my-project --skills committing,branching
EOF
}

TARGET=""
WITH_HOOK=false
FORCE=false
SKILLS_FILTER=""

while [ $# -gt 0 ]; do
    case "$1" in
        --with-hook)
            WITH_HOOK=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --skills)
            SKILLS_FILTER="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -z "$TARGET" ]; then
                TARGET="$1"
            else
                echo "Unexpected argument: $1" >&2
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$TARGET" ]; then
    echo "Error: target project directory is required." >&2
    usage
    exit 1
fi

if [ ! -d "$TARGET" ]; then
    echo "Error: target directory does not exist: $TARGET" >&2
    exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"

echo "Linking agentharness ($HARNESS_DIR) into $TARGET"

# ----------------------------------------------------------------------------
# 1. Skills
# ----------------------------------------------------------------------------
SKILLS_SRC="$HARNESS_DIR/.claude/skills"
SKILLS_DST="$TARGET/.claude/skills"
mkdir -p "$SKILLS_DST"

if [ -d "$SKILLS_SRC" ]; then
    if [ -n "$SKILLS_FILTER" ]; then
        IFS=',' read -ra WANTED <<< "$SKILLS_FILTER"
    else
        WANTED=()
        for d in "$SKILLS_SRC"/*/; do
            [ -d "$d" ] && WANTED+=("$(basename "$d")")
        done
    fi

    for skill in "${WANTED[@]}"; do
        # --skills is user-supplied; reject anything but a plain directory
        # name so "../../etc" or "/etc/passwd"-style values can't make SRC
        # resolve outside SKILLS_SRC and symlink arbitrary harness paths
        # (or worse, arbitrary host paths) into the target project.
        case "$skill" in
            */*|.*|'')
                echo "  Skipping invalid skill name: $skill" >&2
                continue
                ;;
        esac
        SRC="$SKILLS_SRC/$skill"
        DST="$SKILLS_DST/$skill"
        if [ ! -d "$SRC" ]; then
            echo "  Skipping unknown skill: $skill" >&2
            continue
        fi
        if [ -L "$DST" ]; then
            rm "$DST"
        elif [ -e "$DST" ]; then
            echo "  Skipping $skill: $DST exists and is not a symlink (not overwriting)" >&2
            continue
        fi
        ln -s "$SRC" "$DST"
        echo "  Linked skill: $skill"
    done
else
    echo "  No skills found at $SKILLS_SRC yet — skipping." >&2
fi

# ----------------------------------------------------------------------------
# 2. .gitignore
# ----------------------------------------------------------------------------
GITIGNORE_TEMPLATE="$HARNESS_DIR/.github/.gitignore.template"
GITIGNORE_DST="$TARGET/.gitignore"

if [ -f "$GITIGNORE_TEMPLATE" ]; then
    if [ -f "$GITIGNORE_DST" ]; then
        NEW_ENTRIES="$(comm -23 \
            <(grep -vE '^\s*(#|$)' "$GITIGNORE_TEMPLATE" | sort -u) \
            <(grep -vE '^\s*(#|$)' "$GITIGNORE_DST" | sort -u))"
        if [ -n "$NEW_ENTRIES" ]; then
            {
                echo ""
                echo "# --- Added by agentharness harness-link.sh ---"
                echo "$NEW_ENTRIES"
            } >> "$GITIGNORE_DST"
            echo "  Merged new entries into existing .gitignore"
        else
            echo "  .gitignore already covers everything in the template"
        fi
    else
        cp "$GITIGNORE_TEMPLATE" "$GITIGNORE_DST"
        echo "  Created .gitignore from template"
    fi
else
    echo "  No gitignore template found at $GITIGNORE_TEMPLATE — skipping." >&2
fi

# ----------------------------------------------------------------------------
# 3. Trunk-protection hook (opt-in)
# ----------------------------------------------------------------------------
if [ "$WITH_HOOK" = true ]; then
    # `[ -d "$TARGET/.git" ]` misses linked worktrees, where .git is a
    # *file* (`gitdir: /path/to/main/.git/worktrees/name`), not a
    # directory — ask git itself instead of assuming repo layout.
    if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        HOOKS_PATH="$HARNESS_DIR/.github/hooks"
        EXISTING_HOOKS_PATH="$(git -C "$TARGET" config --get core.hooksPath 2>/dev/null || true)"
        if [ -z "$EXISTING_HOOKS_PATH" ] || [ "$EXISTING_HOOKS_PATH" = "$HOOKS_PATH" ]; then
            git -C "$TARGET" config core.hooksPath "$HOOKS_PATH"
            echo "  Installed prevent-trunk-commit + pre-push hooks (core.hooksPath)"
        elif [ "$FORCE" = true ]; then
            git -C "$TARGET" config core.hooksPath "$HOOKS_PATH"
            echo "  Overwrote existing core.hooksPath ($EXISTING_HOOKS_PATH) with agentharness hooks (--force)"
        else
            echo "  --with-hook requested but $TARGET already has a different core.hooksPath set:" >&2
            echo "    $EXISTING_HOOKS_PATH" >&2
            echo "  Not overwriting — rerun with --force to replace it, or run" >&2
            echo "  'git -C $TARGET config --unset core.hooksPath' yourself first." >&2
        fi
    else
        echo "  --with-hook requested but $TARGET is not a git repo — skipping." >&2
    fi
fi

echo "Done."
