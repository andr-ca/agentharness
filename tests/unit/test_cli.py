import argparse
import re
import subprocess
import sys
from pathlib import Path

from agentharness.cli import create_parser, main

EXPECTED_STATUS_JSON = (
    '{"code": "status_available", "details": {"state": "not_configured"}, '
    '"outcome": "success", "remediation": "Run '
    '\'tools/setup/harness-link.sh init\' to install the harness. The '
    'experimental bootstrap policy core is unreleased and has no public '
    'command yet.", "schema_version": 1, '
    '"summary": "Project is not configured."}\n'
)


def test_status_json_has_stable_result_shape(capsys):
    exit_code = main(["status", "--json"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (0, EXPECTED_STATUS_JSON, "")


def test_status_human_output_states_project_is_not_configured(capsys):
    exit_code = main(["status"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (
        0,
        "success: Project is not configured.\n"
        "Next: Run 'tools/setup/harness-link.sh init' to install the "
        "harness. The experimental bootstrap policy core is unreleased "
        "and has no public command yet.\n",
        "",
    )


def test_module_entry_point_emits_stable_status_json():
    project_root = Path(__file__).parents[2]
    completed = subprocess.run(
        [sys.executable, "-m", "agentharness", "status", "--json"],
        cwd=project_root,
        env={"PYTHONPATH": str(project_root / "src")},
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        0,
        EXPECTED_STATUS_JSON,
        "",
    )


def test_invalid_command_is_safe(capsys, monkeypatch):
    secret = "credential-value-that-must-not-leak"
    monkeypatch.setenv("AGENTHARNESS_TOKEN", secret)

    exit_code = main(["unknown-command"])

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert exit_code == 2
    assert "Traceback" not in output
    assert secret not in output


# ---------------------------------------------------------------------------
# Every `Run 'agentharness ...'` remediation the CLI emits must name a command
# that is actually registered. `status` advertised `agentharness bootstrap`
# while `create_parser()` never registered it, so the documented next step
# returned "The command is invalid." — a first-time adopter following the
# tool's own advice hit a dead end.
# ---------------------------------------------------------------------------

REMEDIATION_COMMAND_RE = re.compile(r"Run '(agentharness [^']+)'")


def _registered_command_paths(parser: argparse.ArgumentParser) -> set[tuple[str, ...]]:
    """Every runnable subcommand path, e.g. ('profile', 'apply')."""
    paths: set[tuple[str, ...]] = set()

    def walk(p: argparse.ArgumentParser, prefix: tuple[str, ...]) -> None:
        for action in p._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, sub in action.choices.items():
                    paths.add(prefix + (name,))
                    walk(sub, prefix + (name,))

    walk(parser, ())
    return paths


def _remediation_strings() -> list[str]:
    pkg = Path(__file__).resolve().parents[2] / "src" / "agentharness"
    source = pkg.rglob("*.py")
    found: list[str] = []
    for path in source:
        found += REMEDIATION_COMMAND_RE.findall(path.read_text(encoding="utf-8"))
    return found


def test_remediation_inventory_is_not_empty():
    # Guards against the check passing because the regex stopped matching.
    assert len(_remediation_strings()) >= 3


def test_every_remediation_command_is_actually_registered():
    registered = _registered_command_paths(create_parser())
    broken = []
    for remediation in _remediation_strings():
        # Drop the "agentharness" prefix and any <placeholder> arguments.
        words = [w for w in remediation.split()[1:] if not w.startswith("<")]
        # Match the longest registered prefix of the command path.
        if not any(
            tuple(words[:n]) in registered for n in range(len(words), 0, -1)
        ):
            broken.append(remediation)

    assert broken == [], (
        f"remediation names unrunnable command(s): {broken} — "
        "either register the command or stop advertising it"
    )
