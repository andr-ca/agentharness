import argparse
import re
import subprocess
import sys
from pathlib import Path

from agentharness.cli import create_parser, main

EXPECTED_STATUS_JSON = (
    '{"code": "status_available", "details": {"state": "not_configured"}, '
    '"outcome": "success", "remediation": "Run \'agentharness bootstrap plan\' '
    'to inspect this project.", "schema_version": 1, '
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
        "Next: Run 'agentharness bootstrap plan' to inspect this "
        "project.\n",
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
    # Guards against the check above passing because the regex stopped
    # matching anything. Deliberately `> 0`, not a floor tied to today's
    # count: the guard is "we are still parsing remediations at all", and
    # a legitimate consolidation to fewer of them should not fail it.
    assert len(_remediation_strings()) > 0


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


# ---------------------------------------------------------------------------
# bootstrap: the first-run surface. `plan` must stay read-only, and `apply`
# must refuse anything the owner has not explicitly seen and confirmed.
# ---------------------------------------------------------------------------

BASELINE = ["--answer", "rigor.tier=production", "--answer", "authority.publish=stage"]


def _python_project(root):
    """Minimal Python marker.

    bootstrap only offers adoption to Python projects, so an empty tmp_path
    would take the non-Python path and these tests would assert against a
    plan with no adoption questions at all.
    """
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    return root


def _plan_hash(target, extra):
    import io
    import json as _json

    buffer = io.StringIO()
    main(["bootstrap", "plan", "--target-dir", str(target), "--json", *extra], buffer)
    return _json.loads(buffer.getvalue())["details"]["plan_hash"]


def test_bootstrap_plan_is_registered_and_runs(tmp_path, capsys):
    assert main(["bootstrap", "plan", "--target-dir", str(tmp_path)]) == 0


def test_bootstrap_plan_writes_nothing(tmp_path):
    main(["bootstrap", "plan", "--target-dir", str(tmp_path)])

    assert list(tmp_path.iterdir()) == []


def test_bootstrap_apply_refuses_an_unresolved_plan(tmp_path, capsys):
    exit_code = main(["bootstrap", "apply", "--target-dir", str(tmp_path)])

    assert exit_code == 1
    assert "not resolved" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_bootstrap_apply_refuses_without_a_confirmation_hash(tmp_path, capsys):
    _python_project(tmp_path)
    answers = [*BASELINE, "--answer", "adopt.lint=no", "--answer",
               "adopt.test=no", "--answer", "adopt.types=no"]

    exit_code = main(["bootstrap", "apply", "--target-dir", str(tmp_path), *answers])

    assert exit_code == 1
    assert "without an explicit confirmation" in capsys.readouterr().out


def test_bootstrap_apply_refuses_a_stale_confirmation_hash(tmp_path, capsys):
    _python_project(tmp_path)
    answers = [*BASELINE, "--answer", "adopt.lint=yes", "--answer",
               "adopt.test=no", "--answer", "adopt.types=no"]

    exit_code = main([
        "bootstrap", "apply", "--target-dir", str(tmp_path), *answers,
        "--confirm", "0" * 64,
    ])

    assert exit_code == 1
    assert "does not match" in capsys.readouterr().out
    # Only the marker remains: apply created nothing.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["pyproject.toml"]


def test_bootstrap_apply_writes_only_what_was_confirmed(tmp_path, capsys):
    _python_project(tmp_path)
    answers = [*BASELINE, "--answer", "adopt.lint=yes", "--answer",
               "adopt.test=no", "--answer", "adopt.types=no"]
    digest = _plan_hash(tmp_path, answers)

    exit_code = main([
        "bootstrap", "apply", "--target-dir", str(tmp_path), *answers,
        "--confirm", digest,
    ])

    assert exit_code == 0
    created = sorted(
        p.name for p in tmp_path.iterdir() if p.name != "pyproject.toml"
    )
    assert created == ["ruff.toml"]  # declined capabilities produce nothing


def test_bootstrap_apply_closes_the_loop(tmp_path):
    # What apply writes must be what the next discovery run detects,
    # otherwise the first-run flow would keep re-offering the same setup.
    import io
    import json as _json

    _python_project(tmp_path)
    answers = [*BASELINE, "--answer", "adopt.lint=yes", "--answer",
               "adopt.test=yes", "--answer", "adopt.types=yes"]
    main(["bootstrap", "apply", "--target-dir", str(tmp_path), *answers,
          "--confirm", _plan_hash(tmp_path, answers)])

    buffer = io.StringIO()
    main(["bootstrap", "plan", "--target-dir", str(tmp_path), "--json"], buffer)
    details = _json.loads(buffer.getvalue())["details"]

    present = {d["capability"] for d in details["detected"] if d["present"]}
    assert {"lint", "test", "types"} <= present
    assert not [q for q in details["questions"] if q["id"].startswith("adopt.")]


def test_bootstrap_rejects_a_typod_answer_key(tmp_path, capsys):
    exit_code = main([
        "bootstrap", "plan", "--target-dir", str(tmp_path),
        "--answer", "adpot.lint=yes",
    ])

    assert exit_code == 1
    assert "unknown answer key" in capsys.readouterr().out
