#!/bin/bash
# ============================================================================
# Verify Manifest — Check MANIFEST.md claims against actual files
# ============================================================================
#
# Extracts asset paths from MANIFEST.md's Path column and verifies each
# one actually exists. Catches regressions where docs reference phantom files.
#
# Exit codes: 0 = all entries exist, 1 = missing entries
#
# ============================================================================

MANIFEST_FILE="MANIFEST.md"

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "ERROR: $MANIFEST_FILE not found"
    exit 1
fi

echo "Verifying manifest entries..."
echo ""

# Extract backtick-quoted paths from manifest tables
# These are typically in format: | Asset Name | `path/to/file` | type | description |
# Only extract from pipe-delimited lines, skip headers and separators
grep '|' "$MANIFEST_FILE" | \
    grep -v '^---' | \
    grep -v '^ *$' | \
    grep -v 'Asset\|Path\|Type' | \
    sed 's/|/\n|/g' | \
    grep '`' | \
    grep -o '`[^`]*`' | \
    sed 's/^`//;s/`$//' | \
    # Only process paths (contain / or start with .)
    grep -E '^\.?[^:]*/' | \
    while read -r fullpath; do
        # Skip empty entries
        [ -z "$fullpath" ] && continue

        # Strip anchor references (file.md#section → file.md)
        path="${fullpath%#*}"

        # Skip non-filesystem entries
        [[ "$path" == http* ]] && continue
        [[ "$path" == \#* ]] && continue
        [ -z "$path" ] && continue

        # Check if path exists
        if [ -e "$path" ]; then
            echo "  ✓ $path"
        else
            echo "  ✗ MISSING: $path"
        fi
    done

echo ""

# Final count
found=0
missing=0

grep '|' "$MANIFEST_FILE" | \
    grep -v '^---' | \
    grep -v '^ *$' | \
    grep -v 'Asset\|Path\|Type' | \
    grep -o '`[^`]*`' | \
    sed 's/^`//;s/`$//' | \
    sort -u | \
    while read -r fullpath; do
        [ -z "$fullpath" ] && continue
        path="${fullpath%#*}"
        [[ "$path" == http* ]] && continue
        [[ "$path" == \#* ]] && continue
        [ -z "$path" ] && continue

        if [ -e "$path" ]; then
            ((found++))
        else
            ((missing++))
        fi
    done

# Count missing entries
missing_count=$(grep '|' "$MANIFEST_FILE" | \
    grep -v '^---' | \
    grep -v '^ *$' | \
    grep -v 'Asset\|Path\|Type' | \
    sed 's/|/\n|/g' | \
    grep '`' | \
    grep -o '`[^`]*`' | \
    sed 's/^`//;s/`$//' | \
    grep -E '^\.?[^:]*/' | \
    sort -u | \
    while read -r fullpath; do
        [ -z "$fullpath" ] && continue
        path="${fullpath%#*}"
        [[ "$path" == http* ]] && continue
        [[ "$path" == \#* ]] && continue
        [ -z "$path" ] && continue
        [ ! -e "$path" ] && echo "$path"
    done | wc -l)

if [ "$missing_count" -eq 0 ]; then
    echo "✅ All manifest entries exist."
    exit 0
else
    echo "❌ $missing_count manifest entries missing."
    exit 1
fi
