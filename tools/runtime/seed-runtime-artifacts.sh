#!/usr/bin/env bash
# Portable entrypoint for authenticated, byte-only runtime artifact acquisition.

set -eu

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$REPO_ROOT/tools/runtime/seed-runtime-artifacts.py" "$@"
