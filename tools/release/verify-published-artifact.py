#!/usr/bin/env python3
"""Verify a published npm artifact matches the committed consumer lock.

Usage:
    python3 tools/release/verify-published-artifact.py \\
        --package agentharness-toolkit@0.3.0-rc.1 \\
        --lock-file runtime/python-build-standalone.lock.json

This script is a stub. Task 3 of Slice 6 implements the full verification
against the npm registry and requires publish authority (configured npm
credentials). Until then, this script reports BLOCKED.
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "BLOCKED: artifact verification requires npm registry access.\n"
        "Complete Slice 6 Task 3 with configured registry authority.",
        file=sys.stderr,
    )
    return 2  # BLOCKED, not a failure


if __name__ == "__main__":
    sys.exit(main())
