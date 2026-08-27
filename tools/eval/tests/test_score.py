"""Tests for tools/eval/score.py against hand-written correct/broken
fixtures — the scorer itself makes no LLM calls, so these are ordinary
deterministic unit tests, not evals."""
import shutil
import sys
from pathlib import Path

import pytest

EVAL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_ROOT))

from score import score  # noqa: E402

_NO_GO = pytest.mark.skipif(
    shutil.which("go") is None, reason="go is not installed on this machine"
)

TASKS = [
    "python-input-validation",
    "python-bugfix-average",
    pytest.param("go-error-handling", marks=_NO_GO),
]


@pytest.mark.parametrize("task_id", TASKS)
def test_correct_fixture_scores_perfectly(task_id):
    result = score(
        EVAL_ROOT / "tasks" / task_id, EVAL_ROOT / "fixtures" / task_id / "correct"
    )
    assert result["overall_score"] == 1.0
    assert result["tests_pass"] is True
    assert result["edge_cases_pass"] is True
    assert result["task_id"] == task_id


@pytest.mark.parametrize("task_id", TASKS)
def test_broken_fixture_fails_tests(task_id):
    result = score(
        EVAL_ROOT / "tasks" / task_id, EVAL_ROOT / "fixtures" / task_id / "broken"
    )
    assert result["overall_score"] < 1.0
    assert result["tests_pass"] is False
    assert result["edge_cases_pass"] is False


@pytest.mark.parametrize("task_id", TASKS)
def test_lint_dirty_fixture_fails_lint_only(task_id):
    """Isolates lint_clean: tests and coverage still pass, only lint fails.

    tests_pass/edge_cases_pass are asserted elsewhere (correct/broken
    above); coverage_met and lint_clean were computed by score() but
    never independently asserted anywhere — a regression that always
    reported both as True would have passed every existing test here.

    Go's lint-dirty fixture deliberately uses an `unreachable` vet
    finding, not a printf-verb mismatch: `go test` runs a curated subset
    of vet checks automatically (including printf), so a printf mismatch
    would also fail tests_pass and defeat the isolation this test wants.
    """
    task_dir = EVAL_ROOT / "tasks" / task_id
    result = score(task_dir, EVAL_ROOT / "fixtures" / task_id / "lint-dirty")
    assert result["tests_pass"] is True
    assert result["edge_cases_pass"] is True
    assert result["coverage_met"] is True
    assert result["lint_clean"] is False
    assert result["overall_score"] < 1.0


@pytest.mark.parametrize("task_id", TASKS)
def test_low_coverage_fixture_fails_coverage_only(task_id):
    """Isolates coverage_met: tests and lint still pass, only coverage fails."""
    task_dir = EVAL_ROOT / "tasks" / task_id
    result = score(task_dir, EVAL_ROOT / "fixtures" / task_id / "low-coverage")
    assert result["tests_pass"] is True
    assert result["edge_cases_pass"] is True
    assert result["lint_clean"] is True
    assert result["coverage_met"] is False
    assert result["overall_score"] < 1.0


def test_unsupported_language_raises(tmp_path):
    task_dir = tmp_path / "task"
    (task_dir / "tests").mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        "id: unsupported\nlanguage: rust\nentry_module: main.rs\n"
        "coverage_threshold: 80\nprompt: n/a\n"
    )
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()

    with pytest.raises(ValueError, match="unsupported language"):
        score(task_dir, candidate_dir)
