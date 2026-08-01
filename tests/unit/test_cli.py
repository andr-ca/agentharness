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
        # Drop the "agentharness" prefix, any <placeholder> arguments, and
        # option flags. Flags are not subcommands: "agentharness <command>
        # --help" names a real, runnable affordance, and treating --help as
        # a command path reported it unrunnable. Filtering them keeps the
        # guard pointed at what it is actually checking — that every
        # COMMAND advertised in a remediation exists.
        words = [
            w for w in remediation.split()[1:]
            if not w.startswith("<") and not w.startswith("-")
        ]
        if not words:
            # A remediation naming only flags makes no command claim.
            continue
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
    # Declined capabilities produce nothing. The profile file is the rigor
    # tier from BASELINE being recorded, which is the point of asking it —
    # it is not an adoption scaffold.
    assert created == [".agentharness-profile", "ruff.toml"]
    assert "pytest.ini" not in created
    assert "mypy.ini" not in created


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


# ---------------------------------------------------------------------------
# The interview has to be readable from the command that runs it.
#
# `bootstrap plan` printed a one-line count and said "answer the open
# questions" without ever saying what they were: the questions lived only
# in --json, and every form of --help errored, so a user following the
# instruction had nowhere to go. Found running the published npm package
# against a fresh project.
# ---------------------------------------------------------------------------


def test_plan_prints_the_questions_it_tells_you_to_answer(tmp_path, capsys):
    _python_project(tmp_path)
    main(["bootstrap", "plan", "--target-dir", str(tmp_path)])

    out = capsys.readouterr().out

    # Every open question must appear by id, with its prompt and default:
    # an id alone is not answerable without knowing what it asks.
    assert "rigor.tier" in out
    assert "authority.publish" in out
    assert "Which rigor tier applies" in out
    assert "default: production" in out


def test_plan_prints_the_findings_behind_those_questions(tmp_path, capsys):
    _python_project(tmp_path)
    main(["bootstrap", "plan", "--target-dir", str(tmp_path)])

    out = capsys.readouterr().out

    assert "Findings:" in out
    assert "Linting / formatting" in out


def test_plan_shows_answers_already_supplied(tmp_path, capsys):
    # Answering one at a time, the user needs to see what is settled.
    _python_project(tmp_path)
    main([
        "bootstrap", "plan", "--target-dir", str(tmp_path),
        "--answer", "rigor.tier=prototype",
    ])

    out = capsys.readouterr().out

    assert "rigor.tier = prototype" in out
    assert "authority.publish" in out  # still open


def test_json_output_is_unchanged_by_human_rendering(tmp_path):
    # The renderer lives in the presentation layer precisely so the
    # machine contract does not move.
    import io
    import json as _json

    _python_project(tmp_path)
    buffer = io.StringIO()
    main(["bootstrap", "plan", "--target-dir", str(tmp_path), "--json"], buffer)
    payload = _json.loads(buffer.getvalue())

    assert payload["code"] == "bootstrap_planned"
    assert payload["details"]["questions"]


def test_help_is_available_for_every_bootstrap_command(capsys):
    # All of these errored with "The command is invalid." — the first
    # thing a stuck user tries, on the command built to guide them.
    for argv in (["bootstrap", "--help"],
                 ["bootstrap", "plan", "--help"],
                 ["bootstrap", "apply", "--help"],
                 ["bootstrap", "plan", "-h"]):
        assert main(argv) == 0
        out = capsys.readouterr().out
        assert "error" not in out.lower()
        assert "agentharness bootstrap" in out


def test_help_describes_the_flags_that_drive_the_interview(capsys):
    main(["bootstrap", "plan", "--help"])
    out = capsys.readouterr().out

    assert "--answer" in out
    assert "--target-dir" in out


def test_help_does_not_read_as_a_status_line(capsys):
    # "success: agentharness bootstrap ..." frames docs as a result.
    main(["bootstrap", "--help"])
    assert not capsys.readouterr().out.startswith("success:")


def test_help_falls_back_to_the_nearest_topic(capsys):
    # An unknown subcommand should still get help, not an error.
    assert main(["bootstrap", "nonsuch", "--help"]) == 0
    assert "agentharness bootstrap" in capsys.readouterr().out


def test_remediation_check_still_catches_an_unregistered_command():
    # The flag-filtering above must not turn the guard into a no-op.
    registered = _registered_command_paths(create_parser())
    words = [w for w in "agentharness bootsrap plan --json".split()[1:]
             if not w.startswith("<") and not w.startswith("-")]
    assert words
    assert not any(
        tuple(words[:n]) in registered for n in range(len(words), 0, -1)
    )


def test_proposed_changes_state_their_rationale(tmp_path, capsys):
    # Approving a write means knowing why it is proposed. An earlier cut
    # invented a key the action objects do not have and printed a generic
    # "change: <path>", dropping the rationale entirely.
    _python_project(tmp_path)
    main([
        "bootstrap", "plan", "--target-dir", str(tmp_path),
        "--answer", "rigor.tier=production",
        "--answer", "authority.publish=stage",
        "--answer", "adopt.lint=yes",
        "--answer", "adopt.test=yes",
        "--answer", "adopt.types=yes",
    ])
    out = capsys.readouterr().out

    assert "Create ruff.toml" in out
    assert "you asked to adopt it" in out
    assert "change: " not in out
