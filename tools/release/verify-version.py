#!/usr/bin/env python3
"""Verify version consistency across package.json, src/agentharness/__init__.py,
runtime lock, and Git tag.

Usage:
    python3 tools/release/verify-version.py --expected 0.3.0-rc.1

This script is a stub. Full implementation in Slice 6 Task 3.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", required=True, help="Expected version string")
    parser.add_argument("--tag", help="Expected Git tag (e.g. v0.3.0-rc.1)")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).parent.parent.parent
    errors = []

    # Check package.json
    pkg = json.loads((repo_root / "package.json").read_text())
    pkg_version = pkg.get("version", "")
    if pkg_version != args.expected:
        errors.append(
            f"package.json version {pkg_version!r} != {args.expected!r}"
        )

    # Check Python __init__.py
    init = repo_root / "src" / "agentharness" / "__init__.py"
    if init.exists():
        content = init.read_text()
        if f'__version__ = "{args.expected}"' not in content:
            errors.append(f"__init__.py does not declare version {args.expected!r}")

    if errors:
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1

    print(f"Version {args.expected!r} is consistent across package.json and source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
