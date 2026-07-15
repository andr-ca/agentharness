"""Main Python plugin — detects the Python environment and task runners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentharness.plugins.api import (
    CheckResult,
    Finding,
    FindingCode,
    PluginMetadata,
)
from agentharness.plugins.python.environment import EnvironmentKind, detect_environment
from agentharness.plugins.python.tasks import detect_task_runners


class PythonPlugin:
    """Bootstrap plugin for Python projects.

    Capabilities:
        python.environment  — detects package/dependency management approach.
        python.task_runner  — detects available task runners (tox/nox/make).
    """

    metadata = PluginMetadata(
        plugin_id="agentharness.python",
        display_name="Python Project Plugin",
        version="0.1.0",
        capabilities=["python.environment", "python.task_runner"],
        core_version_range=">=0.1.0",
    )

    def check(self, context: Any) -> CheckResult:
        if isinstance(context, dict):
            root = Path(context.get("project_root", "."))
        else:
            root = Path(".")

        findings: list[Finding] = []

        # Environment detection
        env = detect_environment(root)
        if env.kind == EnvironmentKind.UNKNOWN:
            findings.append(
                Finding(
                    capability="python.environment",
                    code=FindingCode.SKIP,
                    summary="No Python project markers found in this directory.",
                    evidence={"checked_root": str(root)},
                )
            )
        else:
            findings.append(
                Finding(
                    capability="python.environment",
                    code=FindingCode.PASS,
                    summary=f"Detected Python environment: {env.kind}",
                    evidence={
                        "kind": str(env.kind),
                        "has_lock_file": env.has_lock_file,
                        "lock_file_name": env.lock_file_name,
                        "material_files": env.material_files,
                    },
                )
            )

        # Task runner detection
        runners = detect_task_runners(root)
        if not runners:
            findings.append(
                Finding(
                    capability="python.task_runner",
                    code=FindingCode.WARN,
                    summary="No task runner configuration found (tox, nox, Makefile).",
                    evidence={"checked_root": str(root)},
                )
            )
        else:
            findings.append(
                Finding(
                    capability="python.task_runner",
                    code=FindingCode.PASS,
                    summary=f"Detected task runners: {[str(r.kind) for r in runners]}",
                    evidence={
                        "runners": [
                            {
                                "kind": str(r.kind),
                                "config_file": r.config_file,
                                "declared_targets": r.declared_targets,
                            }
                            for r in runners
                        ]
                    },
                )
            )

        return CheckResult(
            plugin_id=self.metadata.plugin_id,
            findings=findings,
        )
