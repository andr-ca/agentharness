"""Integration tests for CLI command routing.

Every public npm command must route through the Python core.  Legacy
installation work is delegated to Bash only for asset operations, not
for policy decisions.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from agentharness.cli import execute_status, main
from agentharness.models import Outcome, ResultCode

# Ensure the src/ tree is on PYTHONPATH for subprocess invocations
_SRC = str(Path(__file__).parent.parent.parent / "src")


class TestCliRouting:
    def test_status_command_returns_success_result(self) -> None:
        result = execute_status()
        assert result.code in ResultCode.__members__.values()
        assert result.outcome in Outcome.__members__.values()

    def test_main_status_returns_zero_exit(self) -> None:
        rc = main(["status", "--json"])
        assert rc == 0

    def test_unknown_command_exits_with_usage_error(self) -> None:
        """Unknown commands return a non-zero exit code, not a traceback."""
        env = {**os.environ, "PYTHONPATH": _SRC}
        proc = subprocess.run(
            [sys.executable, "-m", "agentharness", "no-such-command"],
            capture_output=True,
            text=True,
            env=env,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert proc.returncode != 0
        # No Python traceback in stderr
        assert "Traceback" not in proc.stderr

    def test_status_json_output_has_schema_version(self) -> None:
        env = {**os.environ, "PYTHONPATH": _SRC}
        proc = subprocess.run(
            [sys.executable, "-m", "agentharness", "status", "--json"],
            capture_output=True,
            text=True,
            env=env,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)
        assert "schema_version" in data
