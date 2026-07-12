#!/usr/bin/env bash
# ============================================================================
# harness-link.sh — one-command integration of agentharness into a project
# ============================================================================
#
# Usage:
#   harness-link.sh <target-project-dir> [--with-hook] [--skills skill1,skill2,...]
#
# What it does:
#   1. Symlinks .claude/skills/<name> from this harness into the target
#      project's .claude/skills/ (all skills by default, or a subset via
#      --skills)
#   2. Copies .github/.gitignore.template into the target's .gitignore,
#      merging with any existing .gitignore rather than overwriting it
#   3. With --with-hook: sets core.hooksPath in the target repo to this
#      harness's .github/hooks/ (requires the target to be a git repo).
#      This wires up both hooks git finds there by filename:
#        - pre-commit: blocks direct commits to trunk branches
#        - pre-push: runs the test suite and blocks push below 80% coverage
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
  --skills a,b,c        Comma-separated list of skills to link (default: all)
  -h, --help            Show this help

Example:
  $(basename "$0") ~/my-project --with-hook
  $(basename "$0") ~/my-project --skills committing,branching
EOF
}

TARGET=""
WITH_HOOK=false
SKILLS_FILTER=""

while [ $# -gt 0 ]; do
    case "$1" in
        --with-hook)
            WITH_HOOK=true
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
    if [ -d "$TARGET/.git" ]; then
        git -C "$TARGET" config core.hooksPath "$HARNESS_DIR/.github/hooks"
        echo "  Installed prevent-trunk-commit hook (core.hooksPath)"
    else
        echo "  --with-hook requested but $TARGET is not a git repo — skipping." >&2
    fi
fi

echo "Done."
