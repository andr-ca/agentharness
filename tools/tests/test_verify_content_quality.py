"""Tests for verify-content-quality.py's purpose-built logic: B7's
duplicate-policy detection and B3's bash/console snippet syntax checks.

The rest of that script (YAML/frontmatter validation, Python snippet
checks, generated-file drift) is exercised by running it directly in
CI/check.sh against this repo's real content — no separate test file
existed before B7. This file covers only logic where synthetic tmp_path
fixtures are actually needed: distinguishing a real policy conflict from
legitimate mentions, and proving the syntax checkers fail on a real
syntax error rather than passing vacuously.
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


def test_ignores_worktree_and_node_modules_checkouts(tmp_path):
    # Regression for #83: stale agent-worktree checkouts under
    # .claude/worktrees/ (and third-party docs under node_modules/) are
    # historical snapshots, not current repo content — a conflicting
    # number there must not fail the gate.
    _write_source(tmp_path)
    stale = tmp_path / ".claude" / "worktrees" / "agent-abc" / "docs"
    stale.mkdir(parents=True)
    (stale / "old-review.md").write_text(
        "Coverage must be at least 75% minimum per the old policy.\n"
    )
    deps = tmp_path / ".kilo" / "node_modules" / "some-pkg"
    deps.mkdir(parents=True)
    (deps / "README.md").write_text(
        "Coverage must be at least 99% minimum in this package.\n"
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


# B3: wider runnable-snippet validation. check_python_snippets() (the
# existing precedent this mirrors) has no dedicated test of its own — it's
# only ever exercised against real repo content in CI. These two do get a
# deliberately-broken fixture each, proving the check actually fails on a
# real syntax error rather than passing vacuously no matter what's fed in.


def test_check_bash_snippets_flags_a_real_syntax_error(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(
        "```bash\n"
        "if [ -f foo ]; then\n"
        "  echo missing-fi\n"
        "```\n"
    )

    errors = vcq.check_bash_snippets(sources=[bad])

    assert len(errors) == 1
    assert "bad.md" in errors[0]
    assert "syntax error" in errors[0]


def test_check_bash_snippets_passes_a_valid_multiline_recipe(tmp_path):
    good = tmp_path / "good.md"
    good.write_text(
        "```bash\n"
        "cd ~/my-project\n"
        "cat >> CLAUDE.md <<EOF\n"
        "## Section\n"
        "EOF\n"
        "```\n"
    )

    errors = vcq.check_bash_snippets(sources=[good])

    assert errors == []


def test_check_bash_snippets_reports_missing_source_file(tmp_path):
    errors = vcq.check_bash_snippets(sources=[tmp_path / "nope.md"])

    assert len(errors) == 1
    assert "not found" in errors[0]


def test_check_console_snippets_flags_a_real_syntax_error_in_prompt_lines(tmp_path):
    bad = tmp_path / "bad-demo.md"
    bad.write_text(
        "```console\n"
        "$ if [ -f foo ]; then\n"
        "some output line, not a command\n"
        "```\n"
    )

    errors = vcq.check_console_snippets(sources=[bad])

    assert len(errors) == 1
    assert "bad-demo.md" in errors[0]
    assert "syntax error" in errors[0]


def test_check_console_snippets_ignores_non_prompt_output_lines(tmp_path):
    # Only "$ "-prefixed lines are commands — box-drawing decoration and
    # command output (like docs/DEMO.md's trunk-protection banner) must
    # not be fed to bash -n as if they were shell syntax.
    good = tmp_path / "good-demo.md"
    good.write_text(
        "```console\n"
        "$ echo hello\n"
        "hello\n"
        "╔══════╗\n"
        "$ git status\n"
        "```\n"
    )

    errors = vcq.check_console_snippets(sources=[good])

    assert errors == []


# ---------------------------------------------------------------------------
# check_absence_claims_match_manifest: KNOWN_LIMITATIONS.md is hand-maintained
# and states what the harness does NOT have yet. Those claims go stale silently
# when the thing gets built — docs/KNOWN_LIMITATIONS.md claimed "no API-design
# pattern yet" while patterns/api-design/, a skill, and manifest.yaml all had
# it. manifest.yaml can answer that class of claim mechanically, so the check
# derives the answer rather than asking anyone to remember.
# ---------------------------------------------------------------------------


def _write_limitations(tmp_path: Path, body: str) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "KNOWN_LIMITATIONS.md").write_text(body)


def _write_manifest(tmp_path: Path, paths: list[str]) -> None:
    # Mirrors the real manifest.yaml shape: assets nest under sections[],
    # not a flat top-level list. Getting this wrong made both the check and
    # its fixtures agree on a schema neither had verified, so every case
    # passed for the wrong reason.
    entries = "\n".join(f"    - path: {p}" for p in paths)
    (tmp_path / "manifest.yaml").write_text(
        f"sections:\n  - name: Test\n    assets:\n{entries}\n"
    )


def test_extracts_asset_paths_from_the_real_manifest_schema():
    # Guards the vacuous-pass failure mode directly: if the manifest schema
    # changes, extraction returns nothing and every absence claim would
    # silently pass. The check must report that instead of succeeding.
    import yaml as _yaml

    real = Path(__file__).resolve().parents[2] / "manifest.yaml"
    data = _yaml.safe_load(real.read_text(encoding="utf-8"))
    paths = vcq._manifest_asset_paths(data)

    assert len(paths) > 50
    assert any(p.startswith("patterns/") for p in paths)


def test_reports_a_schema_change_rather_than_passing_vacuously(tmp_path):
    _write_limitations(tmp_path, "- **Patterns:** no api-design pattern yet.\n")
    (tmp_path / "manifest.yaml").write_text("unexpected_key: []\n")

    errors = vcq.check_absence_claims_match_manifest(scan_root=tmp_path)

    assert len(errors) == 1
    assert "schema changed" in errors[0]


def test_flags_an_absence_claim_the_manifest_contradicts(tmp_path):
    _write_manifest(tmp_path, ["patterns/api-design/README.md"])
    _write_limitations(tmp_path, "- **Patterns:** no API-design pattern yet.\n")

    errors = vcq.check_absence_claims_match_manifest(scan_root=tmp_path)

    assert len(errors) == 1
    assert "api-design" in errors[0]
    assert "manifest.yaml" in errors[0]


def test_does_not_flag_an_absence_claim_that_is_still_true(tmp_path):
    _write_manifest(tmp_path, ["patterns/testing/README.md"])
    _write_limitations(tmp_path, "- **Patterns:** no graphql-design pattern yet.\n")

    errors = vcq.check_absence_claims_match_manifest(scan_root=tmp_path)

    assert errors == []


def test_matches_the_asset_kind_not_just_the_name(tmp_path):
    # A skill named api-design must not silence a claim about a *pattern*
    # of the same name — they are different assets in different roots.
    _write_manifest(tmp_path, [".claude/skills/api-design/SKILL.md"])
    _write_limitations(tmp_path, "- **Patterns:** no API-design pattern yet.\n")

    errors = vcq.check_absence_claims_match_manifest(scan_root=tmp_path)

    assert errors == []


def test_is_case_insensitive_about_the_asset_name(tmp_path):
    _write_manifest(tmp_path, ["patterns/api-design/README.md"])
    _write_limitations(tmp_path, "- **Patterns:** no api-design pattern yet.\n")

    errors = vcq.check_absence_claims_match_manifest(scan_root=tmp_path)

    assert len(errors) == 1


def test_no_limitations_file_is_not_an_error(tmp_path):
    _write_manifest(tmp_path, ["patterns/api-design/README.md"])

    assert vcq.check_absence_claims_match_manifest(scan_root=tmp_path) == []


def test_the_real_repo_has_no_contradicted_absence_claims():
    # Guards the actual fix, not just the synthetic cases.
    assert vcq.check_absence_claims_match_manifest() == []


def test_reports_prose_that_parses_to_zero_claims(tmp_path):
    # The exact regression Copilot caught on PR #183: a comma-separated
    # rewording reads fine to a human and matches nothing, silently
    # disabling the check for every item in the list.
    _write_manifest(tmp_path, ["patterns/api-design/README.md"])
    _write_limitations(
        tmp_path,
        "- **Patterns:** no GraphQL, messaging/event-driven, or caching pattern yet.\n",
    )

    errors = vcq.check_absence_claims_match_manifest(scan_root=tmp_path)

    assert len(errors) == 1
    assert "no absence claims matched" in errors[0]


def test_the_real_limitations_file_still_parses_its_claims():
    # Guards the live file against the same silent-disable regression.
    limitations = (
        Path(__file__).resolve().parents[2] / "docs" / "KNOWN_LIMITATIONS.md"
    ).read_text(encoding="utf-8")
    claims = vcq._ABSENCE_CLAIM.findall(limitations)

    assert len(claims) >= 3
    assert {"graphql", "messaging", "caching"} <= {n.lower() for n, _ in claims}


# ---------------------------------------------------------------------------
# check_precedence_matches_docs: the repo has two "which rule wins" ladders
# and both lived only in prose, in three separate places, with nothing
# asserting they agree. precedence.yaml is now the declared source; this
# check keeps the prose honest against it, the same way MANIFEST.md is
# checked against manifest.yaml.
# ---------------------------------------------------------------------------


def _write_precedence(tmp_path: Path, levels: list[str], doc: str) -> None:
    entries = "\n".join(
        f"      - rank: {i}\n        id: l{i}\n        summary: {s}\n"
        f"        mechanizable: true"
        for i, s in enumerate(levels, 1)
    )
    (tmp_path / "precedence.yaml").write_text(
        "ladders:\n"
        "  - id: test_ladder\n"
        "    name: Test ladder\n"
        f"    documented_in: {doc}\n"
        "    levels:\n" + entries + "\n",
        encoding="utf-8",
    )


def test_precedence_passes_when_prose_lists_every_level_in_order(tmp_path):
    _write_precedence(tmp_path, ["Alpha rule", "Beta rule"], "doc.md")
    (tmp_path / "doc.md").write_text(
        "1. **Alpha rule** wins first.\n2. **Beta rule** comes next.\n",
        encoding="utf-8",
    )

    assert vcq.check_precedence_matches_docs(scan_root=tmp_path) == []


def test_precedence_flags_a_level_missing_from_the_prose(tmp_path):
    _write_precedence(tmp_path, ["Alpha rule", "Beta rule"], "doc.md")
    (tmp_path / "doc.md").write_text("1. **Alpha rule** only.\n", encoding="utf-8")

    errors = vcq.check_precedence_matches_docs(scan_root=tmp_path)

    assert len(errors) == 1
    assert "Beta rule" in errors[0]


def test_precedence_flags_prose_that_reorders_the_ladder(tmp_path):
    # Order is the entire content of a precedence rule — a doc that lists
    # the same levels in a different order is wrong, not merely untidy.
    _write_precedence(tmp_path, ["Alpha rule", "Beta rule"], "doc.md")
    (tmp_path / "doc.md").write_text(
        "1. **Beta rule** first.\n2. **Alpha rule** second.\n", encoding="utf-8"
    )

    errors = vcq.check_precedence_matches_docs(scan_root=tmp_path)

    assert len(errors) == 1
    assert "order" in errors[0].lower()


def test_precedence_reports_a_missing_documented_in_target(tmp_path):
    _write_precedence(tmp_path, ["Alpha rule"], "gone.md")

    errors = vcq.check_precedence_matches_docs(scan_root=tmp_path)

    assert len(errors) == 1
    assert "gone.md" in errors[0]


def test_precedence_reports_an_empty_model_rather_than_passing(tmp_path):
    # A file that parses to zero ladders would make every prose doc pass.
    (tmp_path / "precedence.yaml").write_text("ladders: []\n", encoding="utf-8")

    errors = vcq.check_precedence_matches_docs(scan_root=tmp_path)

    assert len(errors) == 1
    assert "no ladders" in errors[0]


def test_precedence_is_silent_when_the_model_is_absent(tmp_path):
    # Consumer repos have no precedence.yaml; the check must not fail them.
    assert vcq.check_precedence_matches_docs(scan_root=tmp_path) == []


def test_the_real_repo_precedence_matches_its_docs():
    assert vcq.check_precedence_matches_docs() == []


def test_the_real_precedence_model_declares_both_ladders():
    # Non-vacuity: guards against the model shrinking to nothing and the
    # check above passing for the wrong reason.
    import yaml as _yaml

    root = Path(__file__).resolve().parents[2]
    model = _yaml.safe_load((root / "precedence.yaml").read_text(encoding="utf-8"))
    ids = {ladder["id"] for ladder in model["ladders"]}

    assert {"rigor_tier", "publish_authority"} <= ids
