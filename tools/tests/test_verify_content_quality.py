"""Tests for B7's duplicate-policy detection in verify-content-quality.py.

The rest of that script is exercised by running it directly in CI/check.sh
against this repo's real content (no separate test file existed before
B7 — this file covers only the new, purpose-built logic, using synthetic
tmp_path fixtures rather than the real repo, since the whole point of
this checker is to distinguish a real conflict from several kinds of
legitimate mention, and that's easiest to prove with fixtures built to
contain exactly one of each.
"""
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "verify-content-quality.py"
spec = importlib.util.spec_from_file_location("verify_content_quality", MODULE_PATH)
vcq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcq)


def _write_source(tmp_path: Path, coverage_line: str = "At Production tier: minimum 80% test coverage.\n") -> None:
    source_dir = tmp_path / "patterns" / "testing"
    source_dir.mkdir(parents=True)
    (source_dir / "COVERAGE_REQUIREMENTS.md").write_text(coverage_line)


def test_flags_a_genuinely_conflicting_number(tmp_path):
    _write_source(tmp_path)
    (tmp_path / "bad.md").write_text("Coverage must be at least 75% for this project.\n")

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert len(errors) == 1
    assert "bad.md" in errors[0]
    assert "75" in errors[0]
    assert "80" in errors[0]


def test_does_not_flag_a_consistent_restatement_with_cross_reference(tmp_path):
    _write_source(tmp_path)
    (tmp_path / "good.md").write_text(
        "Coverage >= 80% (minimum requirement) -- see COVERAGE_REQUIREMENTS.md.\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_does_not_flag_a_measured_result_description(tmp_path):
    # The real false positive B7 caught during implementation:
    # .claude/skills/agentic-loops/SKILL.md's "(100% coverage)" describes
    # one file's *measured* test result, not a restated mandate — no
    # mandate-signal word (minimum/required/below/>=/<) appears near it.
    _write_source(tmp_path)
    (tmp_path / "unrelated.md").write_text(
        "This module is tested (100% coverage) as a reference implementation.\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_does_not_flag_an_aspirational_stretch_goal_on_an_adjacent_line(tmp_path):
    # The real false positive from the character-window design (rejected
    # during implementation in favor of per-line matching): a checklist's
    # "(minimum requirement)" on one line must not leak into an adjacent
    # "Strive for 90%+ coverage" line and make it look like a restated,
    # conflicting mandate.
    _write_source(tmp_path)
    (tmp_path / "checklist.md").write_text(
        "- [ ] Coverage >= 80% (minimum requirement)\n"
        "- [ ] Strive for 90%+ coverage\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_ignores_fenced_code_blocks(tmp_path):
    # An illustrative example (e.g. README.md's before/after drift demo)
    # showing a *hypothetical* project's wrong number isn't this repo's
    # actual policy and must not be scanned as if it were.
    _write_source(tmp_path)
    (tmp_path / "example.md").write_text(
        "Some prose.\n\n"
        "```markdown\n"
        "Coverage must be at least 70% minimum for this project.\n"
        "```\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_ignores_excluded_directories_and_filenames(tmp_path):
    _write_source(tmp_path)
    (tmp_path / "docs" / "operational" / "reviews").mkdir(parents=True)
    (tmp_path / "docs" / "operational" / "reviews" / "old-review.md").write_text(
        "Coverage must be at least 75% minimum in the old policy.\n"
    )
    (tmp_path / "examples" / "python-project").mkdir(parents=True)
    (tmp_path / "examples" / "python-project" / "README.md").write_text(
        "Aim for 75% coverage minimum in this fixture.\n"
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "Coverage must be at least 75% minimum, changed from the old value.\n"
    )

    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert errors == []


def test_reports_a_clear_error_when_source_of_truth_file_is_missing(tmp_path):
    errors = vcq.check_duplicate_policy_numbers(scan_root=tmp_path)

    assert len(errors) == 1
    assert "not found" in errors[0]
