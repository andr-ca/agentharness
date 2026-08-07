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


def test_precedence_reports_a_directory_named_like_the_model(tmp_path):
    # exists() is true for a directory; read_text() then raises and would
    # crash the entire content-quality gate rather than reporting.
    (tmp_path / "precedence.yaml").mkdir()

    errors = vcq.check_precedence_matches_docs(scan_root=tmp_path)

    assert len(errors) == 1
    assert "not a regular file" in errors[0]


def test_precedence_reports_an_unreadable_documented_in_target(tmp_path):
    _write_precedence(tmp_path, ["Alpha rule"], "doc.md")
    (tmp_path / "doc.md").mkdir()  # present but not readable as text

    errors = vcq.check_precedence_matches_docs(scan_root=tmp_path)

    assert len(errors) == 1
    assert "doc.md" in errors[0]


def test_absence_check_survives_a_directory_named_like_the_manifest(tmp_path):
    _write_limitations(tmp_path, "- **Patterns:** no graphql pattern yet.\n")
    (tmp_path / "manifest.yaml").mkdir()

    # Must not raise; a malformed layout is not this check's to report.
    assert vcq.check_absence_claims_match_manifest(scan_root=tmp_path) == []


# ---------------------------------------------------------------------------
# check_no_force_push_instructions: the repo-wide no-force-push-any-branch
# ruleset has no bypass actors, so any doc telling a reader to force-push is
# advice that cannot work. Two such instructions existed in
# COMMITTING_GUIDELINES.md alone. Narrow and targeted, like the numeric
# policy registry — not a general same-rule-drift detector, which would
# need per-rule exclusions rivalling the rule count.
# ---------------------------------------------------------------------------


def test_flags_a_force_push_command_in_a_fenced_block(tmp_path):
    (tmp_path / "guide.md").write_text(
        "Push it:\n\n```bash\ngit push --force-with-lease\n```\n", encoding="utf-8"
    )

    errors = vcq.check_no_force_push_instructions(scan_root=tmp_path)

    assert len(errors) == 1
    assert "guide.md" in errors[0]


def test_flags_plain_force_too(tmp_path):
    (tmp_path / "guide.md").write_text(
        "```bash\ngit push --force\n```\n", encoding="utf-8"
    )

    assert len(vcq.check_no_force_push_instructions(scan_root=tmp_path)) == 1


def test_does_not_flag_prose_explaining_that_force_push_is_blocked(tmp_path):
    # The rule's own explanation must not trip its own check, or the fix
    # for a violation becomes a violation.
    (tmp_path / "guide.md").write_text(
        "`--force-with-lease` does not help: the push is still "
        "non-fast-forward and the ruleset rejects it.\n",
        encoding="utf-8",
    )

    assert vcq.check_no_force_push_instructions(scan_root=tmp_path) == []


def test_does_not_flag_a_commented_out_line_in_a_fence(tmp_path):
    # A commented line inside a fence is explanation, not instruction.
    (tmp_path / "guide.md").write_text(
        "```bash\n# git push --force-with-lease does not work here\ngit push\n```\n",
        encoding="utf-8",
    )

    assert vcq.check_no_force_push_instructions(scan_root=tmp_path) == []


def test_the_real_repo_has_no_force_push_instructions():
    assert vcq.check_no_force_push_instructions() == []


def test_a_declared_exception_is_allowed(tmp_path):
    (tmp_path / "guide.md").write_text(
        "```bash\n# agentharness:force-push-exception — purging a secret\n"
        "git push --force\n```\n",
        encoding="utf-8",
    )

    assert vcq.check_no_force_push_instructions(scan_root=tmp_path) == []


def test_an_exception_in_one_fence_does_not_excuse_another(tmp_path):
    # Scoped per fence, not per file — otherwise one legitimate exception
    # would silently license every force-push in the same document.
    (tmp_path / "guide.md").write_text(
        "```bash\n# agentharness:force-push-exception\ngit push --force\n```\n"
        "\nUnrelated:\n\n```bash\ngit push --force-with-lease\n```\n",
        encoding="utf-8",
    )

    errors = vcq.check_no_force_push_instructions(scan_root=tmp_path)

    assert len(errors) == 1
    assert "force-with-lease" in errors[0]


def _write_context_entry(tmp_path: Path, target: str = "target.md", **overrides) -> None:
    (tmp_path / target).write_text("stub\n", encoding="utf-8")
    entry = {
        "id": "test-entry",
        "path": target,
        "kind": "policy",
        "authority": "none",
        "lifecycle": "durable",
        "loading": "on-demand",
        "provenance": "verified",
        "freshness": {"last_verified": "2026-08-06", "invalidate_on": [target]},
    }
    entry.update(overrides)
    import yaml as _yaml

    (tmp_path / "context.yaml").write_text(
        _yaml.dump({"entries": [entry]}, sort_keys=False), encoding="utf-8"
    )


def test_context_yaml_missing_file_is_not_an_error(tmp_path):
    assert vcq.check_context_yaml_valid(scan_root=tmp_path) == []


def test_context_yaml_valid_entry_passes(tmp_path):
    _write_context_entry(tmp_path)

    assert vcq.check_context_yaml_valid(scan_root=tmp_path) == []


def test_context_yaml_reports_missing_field(tmp_path):
    _write_context_entry(tmp_path)
    (tmp_path / "context.yaml").write_text(
        "entries:\n  - id: test-entry\n    path: target.md\n", encoding="utf-8"
    )

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert len(errors) == 1
    assert "missing field(s)" in errors[0]


def test_context_yaml_reports_missing_path(tmp_path):
    _write_context_entry(tmp_path, target="nonexistent.md")
    (tmp_path / "nonexistent.md").unlink()

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("does not exist" in e for e in errors)


def test_context_yaml_reports_invalid_kind(tmp_path):
    _write_context_entry(tmp_path, kind="not-a-real-kind")

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid kind" in e for e in errors)


def test_context_yaml_reports_invalid_lifecycle(tmp_path):
    _write_context_entry(tmp_path, lifecycle="forever")

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid lifecycle" in e for e in errors)


def test_context_yaml_reports_invalid_loading(tmp_path):
    _write_context_entry(tmp_path, loading="sometimes")

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid loading" in e for e in errors)


def test_context_yaml_reports_invalid_provenance(tmp_path):
    _write_context_entry(tmp_path, provenance="probably")

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid provenance" in e for e in errors)


def test_context_yaml_reports_incomplete_freshness(tmp_path):
    _write_context_entry(tmp_path, freshness={"last_verified": "2026-08-06"})

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("incomplete freshness" in e for e in errors)


def test_context_yaml_reports_freshness_watching_a_missing_path(tmp_path):
    _write_context_entry(tmp_path, freshness={"last_verified": "2026-08-06", "invalidate_on": ["ghost.md"]})

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("does not exist" in e and "ghost.md" in e for e in errors)


def test_context_yaml_rejects_an_absolute_invalidate_on_path(tmp_path):
    _write_context_entry(
        tmp_path, freshness={"last_verified": "2026-08-06", "invalidate_on": ["/etc/passwd"]}
    )

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid invalidate_on" in e for e in errors)


def test_context_yaml_rejects_a_traversal_invalidate_on_path(tmp_path):
    _write_context_entry(
        tmp_path, freshness={"last_verified": "2026-08-06", "invalidate_on": ["../outside.md"]}
    )

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid invalidate_on" in e for e in errors)


def test_context_yaml_rejects_a_non_string_invalidate_on_entry(tmp_path):
    _write_context_entry(tmp_path, freshness={"last_verified": "2026-08-06", "invalidate_on": [{"a": 1}]})

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("invalid invalidate_on" in e for e in errors)


def test_context_yaml_reports_duplicate_id(tmp_path):
    (tmp_path / "a.md").write_text("stub\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("stub\n", encoding="utf-8")
    entry = {
        "id": "dup",
        "path": "a.md",
        "kind": "policy",
        "authority": "none",
        "lifecycle": "durable",
        "loading": "on-demand",
        "provenance": "verified",
        "freshness": {"last_verified": "2026-08-06", "invalidate_on": ["a.md"]},
    }
    entry2 = dict(entry, path="b.md", freshness={"last_verified": "2026-08-06", "invalidate_on": ["b.md"]})
    import yaml as _yaml

    (tmp_path / "context.yaml").write_text(
        _yaml.dump({"entries": [entry, entry2]}, sort_keys=False), encoding="utf-8"
    )

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("duplicate id" in e for e in errors)


def test_context_yaml_authority_must_be_a_real_ladder_or_none(tmp_path):
    _write_context_entry(tmp_path, authority="made-up-ladder")
    (tmp_path / "precedence.yaml").write_text(
        "ladders:\n  - id: rigor_tier\n    levels: []\n", encoding="utf-8"
    )

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert any("not a ladder id" in e for e in errors)


def test_context_yaml_no_entries_reports_schema_change(tmp_path):
    (tmp_path / "context.yaml").write_text("entries: []\n", encoding="utf-8")

    errors = vcq.check_context_yaml_valid(scan_root=tmp_path)

    assert len(errors) == 1
    assert "no entries declared" in errors[0]


def test_the_real_context_yaml_is_valid():
    # Integration check: the real committed context.yaml must itself pass
    # every rule this function enforces.
    errors = vcq.check_context_yaml_valid()

    assert errors == []


def _git(tmp_path: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)


def _init_git_repo(tmp_path: Path) -> None:
    _git(tmp_path, "init", "--quiet")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")


def _commit_file(tmp_path: Path, rel_path: str, content: str, date_iso: str) -> None:
    (tmp_path / rel_path).write_text(content, encoding="utf-8")
    _git(tmp_path, "add", rel_path)
    import subprocess

    env_commit = ["git", "commit", "--quiet", "-m", f"update {rel_path}"]
    subprocess.run(
        env_commit,
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_DATE": date_iso,
            "GIT_COMMITTER_DATE": date_iso,
        },
    )


def _write_freshness_context(tmp_path: Path, last_verified: str, authority: str = "none") -> None:
    entry = {
        "id": "watched-entry",
        "path": "watched.md",
        "kind": "policy",
        "authority": authority,
        "lifecycle": "durable",
        "loading": "on-demand",
        "provenance": "verified",
        "freshness": {"last_verified": last_verified, "invalidate_on": ["watched.md"]},
    }
    import yaml as _yaml

    (tmp_path / "context.yaml").write_text(
        _yaml.dump({"entries": [entry]}, sort_keys=False), encoding="utf-8"
    )


def test_context_freshness_no_git_repo_is_not_an_error(tmp_path):
    _write_freshness_context(tmp_path, last_verified="2026-08-06")
    (tmp_path / "watched.md").write_text("stub\n", encoding="utf-8")

    errors, warnings = vcq.check_context_freshness(scan_root=tmp_path)

    assert errors == []
    assert warnings == []


def test_context_freshness_flags_a_stale_advisory_entry_as_a_warning(tmp_path):
    _init_git_repo(tmp_path)
    _write_freshness_context(tmp_path, last_verified="2026-01-01", authority="none")
    _commit_file(tmp_path, "watched.md", "changed\n", "2026-06-01T00:00:00")
    _git(tmp_path, "add", "context.yaml")
    _git(tmp_path, "commit", "--quiet", "-m", "add context.yaml")

    errors, warnings = vcq.check_context_freshness(scan_root=tmp_path)

    assert errors == []
    assert len(warnings) == 1
    assert "watched-entry" in warnings[0]


def test_context_freshness_flags_a_stale_ladder_entry_as_an_error(tmp_path):
    _init_git_repo(tmp_path)
    _write_freshness_context(tmp_path, last_verified="2026-01-01", authority="rigor_tier")
    _commit_file(tmp_path, "watched.md", "changed\n", "2026-06-01T00:00:00")
    _git(tmp_path, "add", "context.yaml")
    _git(tmp_path, "commit", "--quiet", "-m", "add context.yaml")

    errors, warnings = vcq.check_context_freshness(scan_root=tmp_path)

    assert warnings == []
    assert len(errors) == 1
    assert "watched-entry" in errors[0]


def test_context_freshness_passes_when_verified_after_the_change(tmp_path):
    _init_git_repo(tmp_path)
    _write_freshness_context(tmp_path, last_verified="2026-06-15", authority="none")
    _commit_file(tmp_path, "watched.md", "changed\n", "2026-06-01T00:00:00")
    _git(tmp_path, "add", "context.yaml")
    _git(tmp_path, "commit", "--quiet", "-m", "add context.yaml")

    errors, warnings = vcq.check_context_freshness(scan_root=tmp_path)

    assert errors == []
    assert warnings == []


def test_context_freshness_skips_an_invalid_invalidate_on_path(tmp_path):
    _init_git_repo(tmp_path)
    entry = {
        "id": "watched-entry",
        "path": "watched.md",
        "kind": "policy",
        "authority": "none",
        "lifecycle": "durable",
        "loading": "on-demand",
        "provenance": "verified",
        "freshness": {"last_verified": "2026-01-01", "invalidate_on": ["../outside.md"]},
    }
    import yaml as _yaml

    (tmp_path / "context.yaml").write_text(_yaml.dump({"entries": [entry]}, sort_keys=False), encoding="utf-8")
    _git(tmp_path, "add", "context.yaml")
    _git(tmp_path, "commit", "--quiet", "-m", "add context.yaml")

    errors, warnings = vcq.check_context_freshness(scan_root=tmp_path)

    assert errors == []
    assert warnings == []


def test_the_real_context_yaml_has_no_stale_ladder_entries():
    # Integration check: whatever advisory staleness exists in the real
    # repo, no authority-bearing (ladder) entry may be stale — that half
    # is a hard failure by design.
    errors, _warnings = vcq.check_context_freshness()

    assert errors == []
