"""Compatibility plugin — delegates enforcement to the legacy Bash provider.

The compatibility provider invokes ``tools/setup/harness-link.sh`` for
installation-only work, while the Python core retains orchestration and
result semantics.  The Bash interface is preserved for direct users;
only the npm CLI routes through this adapter.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class CompatibilityProvider:
    """A plugin that delegates enforcement to the legacy Bash provider.

    This is a locked provider: the path and command are resolved once at
    construction time and verified to exist before use.  The provider
    never makes policy decisions; it executes the legacy script and
    returns its exit code.
    """

    def __init__(self, harness_root: Path) -> None:
        self._script = harness_root / "tools" / "setup" / "harness-link.sh"
        if not self._script.exists():
            raise FileNotFoundError(
                f"Legacy compatibility script not found: {self._script}"
            )

    def enforce_profile(self, project_root: Path) -> int:
        """Run the legacy enforce-profile check and return its exit code."""
        result = subprocess.run(
            ["bash", str(self._script), "enforce-profile"],
            cwd=project_root,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode

    def status(self, project_root: Path) -> int:
        """Run the legacy status check and return its exit code."""
        result = subprocess.run(
            ["bash", str(self._script), "status"],
            cwd=project_root,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode
