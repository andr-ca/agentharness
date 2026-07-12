#!/bin/bash
# ============================================================================
# Verify Manifest — Check MANIFEST.md claims against actual files
# ============================================================================
#
# Bidirectional check:
#   1. Forward:  every backtick-quoted path in MANIFEST.md must exist.
#   2. Reverse:  every git-tracked file must be covered by some manifest
#      entry (either an exact path, or a directory entry ending in `/`
#      that the file lives under) — unless explicitly excluded below.
#
# This catches both phantom entries (docs pointing at deleted/renamed
# files) and unlisted assets (new files that never made it into the index).
#
# Exit codes: 0 = manifest matches repo state, 1 = drift found
#
# ============================================================================
set -euo pipefail

MANIFEST_FILE="MANIFEST.md"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "ERROR: $MANIFEST_FILE not found"
    exit 1
fi

# Tracked files that are intentionally not individually indexed:
#   - .gitignore is local/generated-style config, not a reference asset
#   - MANIFEST.md indexes everything else, not itself
EXCLUDE_PATTERNS=(
    '^\.gitignore$'
    '^MANIFEST\.md$'
)

is_excluded() {
    local f="$1" pat
    for pat in "${EXCLUDE_PATTERNS[@]}"; do
        [[ "$f" =~ $pat ]] && return 0
    done
    return 1
}

echo "Verifying manifest entries..."
echo ""

# ---- Extract every backtick-quoted path from MANIFEST.md's tables ----
# Every table in this file has the shape `| Asset | Path | Type | ... |`,
# so the Path cell is always the 3rd pipe-delimited field (field 1 is the
# empty text before the leading `|`). Reading only that field — instead of
# every backtick span in the row — avoids treating inline code in the
# "When to use" column (e.g. `pre-commit`, `core.hooksPath`) as a path.
mapfile -t manifest_paths < <(
    grep '^|' "$MANIFEST_FILE" |
    awk -F'|' '{print $3}' |
    grep '`' |
    grep -o '`[^`]*`' |
    sed 's/^`//; s/`$//' |
    sed 's/#.*$//' |
    grep -vE '^https?://' |
    grep -v '^$' |
    sort -u
)

# ---- Forward check: every listed path must exist on disk ----
forward_missing=0
for path in "${manifest_paths[@]}"; do
    if [ -e "$path" ]; then
        echo "  ✓ $path"
    else
        echo "  ✗ MISSING: $path"
        forward_missing=$((forward_missing + 1))
    fi
done

echo ""

# ---- Reverse check: every tracked file must be covered by some entry ----
is_covered() {
    local f="$1" p
    for p in "${manifest_paths[@]}"; do
        if [[ "$p" == */ ]]; then
            [[ "$f" == "$p"* ]] && return 0
        elif [[ "$f" == "$p" ]]; then
            return 0
        fi
    done
    return 1
}

reverse_missing=0
while IFS= read -r tracked_file; do
    is_excluded "$tracked_file" && continue
    if ! is_covered "$tracked_file"; then
        echo "  ✗ UNLISTED: $tracked_file (tracked but not in $MANIFEST_FILE)"
        reverse_missing=$((reverse_missing + 1))
    fi
done < <(git ls-files)

echo ""

if [ "$forward_missing" -eq 0 ] && [ "$reverse_missing" -eq 0 ]; then
    echo "✅ Manifest matches repo state (${#manifest_paths[@]} entries verified)."
    exit 0
else
    echo "❌ $forward_missing manifest entries missing on disk, $reverse_missing tracked files not listed in manifest."
    exit 1
fi
