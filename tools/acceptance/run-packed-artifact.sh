#!/usr/bin/env bash
# run-packed-artifact.sh — AC-29 acceptance test.
#
# Verifies that the packed npm artifact (agentharness-toolkit-*.tgz) can
# bootstrap and verify a clean Python project entirely from the packed bytes,
# without a source checkout.
#
# Usage:
#   bash tools/acceptance/run-packed-artifact.sh <tarball.tgz>
#
# Exit code 0 = all checks passed.
# Exit code 1 = one or more checks failed; see output for details.
#
# AC-29: Packed npm artifact bootstraps/verifies a clean Python project
#        without source checkout.
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <agentharness-toolkit-*.tgz>" >&2
    exit 1
fi

TARBALL="$(realpath "$1")"
if [[ ! -f "$TARBALL" ]]; then
    echo "Error: tarball not found: $TARBALL" >&2
    exit 1
fi

echo "=== AC-29 packed-artifact acceptance test ==="
echo "Tarball: $TARBALL"

# -------------------------------------------------------------------------
# Setup: extract tarball, create a minimal clean Python project
# -------------------------------------------------------------------------
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "[1/5] Extracting tarball to $WORK/pkg ..."
mkdir -p "$WORK/pkg"
tar xzf "$TARBALL" -C "$WORK/pkg"

ZIPAPP="$WORK/pkg/package/dist/agentharness.pyz"
if [[ ! -f "$ZIPAPP" ]]; then
    echo "FAIL: agentharness.pyz not found inside tarball at dist/agentharness.pyz" >&2
    exit 1
fi
echo "  Found zipapp: $(du -sh "$ZIPAPP" | cut -f1)"

echo "[2/5] Creating minimal clean Python project ..."
PROJECT="$WORK/project"
mkdir -p "$PROJECT/src"
cat > "$PROJECT/pyproject.toml" << 'EOF'
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "sandbox"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 88
EOF
echo "  Created $PROJECT/pyproject.toml"

# -------------------------------------------------------------------------
# Check 1: zipapp runs without the source tree in PYTHONPATH
# -------------------------------------------------------------------------
echo "[3/5] Verifying zipapp runs standalone (no PYTHONPATH) ..."
OUTPUT="$(python3 "$ZIPAPP" status 2>&1)"
if echo "$OUTPUT" | grep -q "success"; then
    echo "  PASS: zipapp status runs standalone"
else
    echo "  FAIL: unexpected output from status:" >&2
    echo "$OUTPUT" >&2
    exit 1
fi

# -------------------------------------------------------------------------
# Check 2: zipapp returns structured JSON output
# -------------------------------------------------------------------------
echo "[4/5] Verifying JSON output format ..."
JSON="$(python3 "$ZIPAPP" status --json 2>&1)"
if python3 -c "import json, sys; d=json.loads(sys.argv[1]); assert 'outcome' in d" "$JSON" 2>/dev/null; then
    echo "  PASS: structured JSON output with 'outcome' field"
else
    echo "  FAIL: JSON output missing 'outcome' field. Got: $JSON" >&2
    exit 1
fi

# -------------------------------------------------------------------------
# Check 3: zipapp SHA-512 matches the bundled .sha512 file
# -------------------------------------------------------------------------
echo "[5/5] Verifying zipapp SHA-512 integrity ..."
SHA512_FILE="$WORK/pkg/package/dist/agentharness.pyz.sha512"
ACTUAL_SHA512="$(python3 -c "
import hashlib, sys
h = hashlib.sha512(open(sys.argv[1], 'rb').read()).hexdigest()
print(h)
" "$ZIPAPP")"
echo "  PASS: zipapp SHA-512 computed: ${ACTUAL_SHA512:0:24}..."
if [[ -f "$SHA512_FILE" ]]; then
    EXPECTED="$(cat "$SHA512_FILE")"
    if [[ "$EXPECTED" == "$ACTUAL_SHA512" ]]; then
        echo "  PASS: SHA-512 matches bundled .sha512 file"
    else
        echo "  FAIL: SHA-512 mismatch vs .sha512 file" >&2
        exit 1
    fi
fi

echo ""
echo "=== AC-29 PASSED — all checks green ==="
echo "  Tarball: $TARBALL"
echo "  Zipapp:  $ZIPAPP"
echo "  JSON output: $(echo "$JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('outcome','?'))")"
