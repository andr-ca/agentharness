"""Tests for the bootstrap plan composer.

A plan is the contract between discovery and apply. It must be
deterministic (same repo + same answers => same hash), it must never
propose changing something the repo already has, and it must stay
unresolved until every question has an answer — apply is gated on that.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentharness.bootstrap.plan import build_plan


def _write(root: Path, rel: str, content: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _python_project(root: Path) -> Path:
    """Minimal Python marker.

    These tests exercise plan composition, not language detection — but an
    empty directory is (correctly) not a Python project, so without a
    marker they would assert against the non-Python path and prove nothing
    about the logic they name.
    """
    _write(root, "pyproject.toml", '[project]\nname = "demo"\n')
    return root


def test_empty_project_asks_the_baseline_questions(tmp_path):
    plan = build_plan(tmp_path)
    ids = {q.id for q in plan.questions.questions}

    assert "rigor.tier" in ids
    assert "authority.publish" in ids


def test_absent_capabilities_become_adoption_questions(tmp_path):
    _python_project(tmp_path)
    plan = build_plan(tmp_path)
    ids = {q.id for q in plan.questions.questions}

    assert "adopt.lint" in ids
    assert "adopt.test" in ids


def test_a_detected_capability_is_never_offered_for_adoption(tmp_path):
    # Preserving what the repo already does is the whole point of
    # discovery — bootstrap must not propose replacing a working setup.
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\n")

    plan = build_plan(tmp_path)

    assert "adopt.lint" not in {q.id for q in plan.questions.questions}
    assert all(a.capability != "lint" for a in plan.actions)


def test_plan_is_unresolved_until_every_question_is_answered(tmp_path):
    assert not build_plan(tmp_path).is_resolved


def test_plan_becomes_resolved_when_all_answers_are_supplied(tmp_path):
    plan = build_plan(tmp_path)
    answers = {q.id: (q.default or "no") for q in plan.questions.questions}

    assert build_plan(tmp_path, answers=answers).is_resolved


def test_answering_yes_produces_an_action_for_that_capability(tmp_path):
    _python_project(tmp_path)
    plan = build_plan(tmp_path, answers={"adopt.lint": "yes"})

    assert any(a.capability == "lint" for a in plan.actions)


def test_answering_no_produces_no_action_for_that_capability(tmp_path):
    _python_project(tmp_path)
    plan = build_plan(tmp_path, answers={"adopt.lint": "no"})

    assert all(a.capability != "lint" for a in plan.actions)


def test_hash_is_stable_across_identical_builds(tmp_path):
    _python_project(tmp_path)
    answers = {"adopt.lint": "yes", "rigor.tier": "production"}

    first = build_plan(tmp_path, answers=answers)
    second = build_plan(tmp_path, answers=answers)

    assert first.plan_hash == second.plan_hash


def test_hash_changes_when_an_answer_changes(tmp_path):
    # apply --confirm <hash> relies on this: a plan the owner did not see
    # must not pass confirmation.
    _python_project(tmp_path)
    yes = build_plan(tmp_path, answers={"adopt.lint": "yes"})
    no = build_plan(tmp_path, answers={"adopt.lint": "no"})

    assert yes.plan_hash != no.plan_hash


def test_hash_changes_when_the_repository_changes(tmp_path):
    before = build_plan(tmp_path).plan_hash
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\n")

    assert build_plan(tmp_path).plan_hash != before


def test_unknown_answer_keys_are_rejected(tmp_path):
    # A typo'd --answer must fail loudly rather than silently doing
    # nothing and leaving the plan unresolved for an unexplained reason.
    try:
        build_plan(tmp_path, answers={"adpot.lint": "yes"})
    except ValueError as exc:
        assert "adpot.lint" in str(exc)
    else:
        raise AssertionError("expected ValueError for an unknown answer key")


def test_actions_never_target_an_existing_file(tmp_path):
    # A file sitting at a scaffold path that detection does NOT recognise
    # as config — the capability still reads absent, so adoption is
    # offered, but the file must not be clobbered. (A *recognised* config
    # can't reach this path: it would mark the capability present and the
    # adoption question would never be asked.)
    # Deliberately contains no pytest section header. (Not even inside a
    # comment: detection does a substring match, so mentioning the header
    # in prose is enough to register as configured.)
    _python_project(tmp_path)
    _write(tmp_path, "pytest.ini", "# hand-written placeholder\n")

    plan = build_plan(tmp_path, answers={"adopt.test": "yes"})

    assert not plan.inventory.capability("test").present
    assert all(a.path != "pytest.ini" for a in plan.actions)
    for action in plan.actions:
        assert not (tmp_path / action.path).exists()


def test_plan_serialises_to_json_safe_primitives(tmp_path):
    import json

    payload = build_plan(tmp_path).to_dict()

    assert json.loads(json.dumps(payload))["plan_hash"]


# ---------------------------------------------------------------------------
# Non-Python projects. Every detector and every scaffold here is Python-only,
# and they were applied unconditionally — so a Go repo was told it had no test
# framework (while holding *_test.go files), offered adoption, and on apply
# received ruff.toml, pytest.ini and mypy.ini. Writing another language's
# tooling into a project is worse than reporting nothing.
# ---------------------------------------------------------------------------


def _write_go_project(root: Path) -> None:
    _write(root, "go.mod", "module example.com/demo\n\ngo 1.22\n")
    _write(root, "main.go", "package main\n")
    _write(root, "main_test.go", "package main\n")


def test_a_go_project_gets_no_adoption_questions(tmp_path):
    _write_go_project(tmp_path)

    ids = {q.id for q in build_plan(tmp_path).questions.questions}

    assert not [i for i in ids if i.startswith("adopt.")]


def test_a_go_project_gets_no_actions_even_when_answers_are_forced(tmp_path):
    # The harmful path: an answer file carried over from another project
    # must not cause Python configs to land in a Go repo.
    _write_go_project(tmp_path)

    # Forced, because with no answers there would be no actions anyway and
    # the test would pass without exercising anything.
    plan = build_plan(tmp_path, answers={"rigor.tier": "production"})

    # Narrowed to what this test actually guards, per its own comment: no
    # PYTHON config may land here. The rigor tier is a harness-level
    # decision and is language-agnostic, so recording it in a Go repo is
    # correct — asserting no actions at all would forbid that too.
    assert not [
        a for a in plan.actions
        if a.path in ("ruff.toml", "pytest.ini", "mypy.ini")
    ]
    # And an adoption answer must be rejected outright, not silently ignored:
    # the question does not exist for this project.
    try:
        build_plan(tmp_path, answers={"adopt.lint": "yes"})
    except ValueError as exc:
        assert "adopt.lint" in str(exc)
    else:
        raise AssertionError("expected adopt.lint to be an unknown key here")


def test_a_go_project_still_asks_the_baseline_questions(tmp_path):
    # Rigor tier and publish authority are language-independent, and the
    # owner of a Go repo still needs the harness configured.
    _write_go_project(tmp_path)

    ids = {q.id for q in build_plan(tmp_path).questions.questions}

    assert {"rigor.tier", "authority.publish"} <= ids


def test_a_go_project_does_not_claim_python_capabilities_are_absent(tmp_path):
    # "No linter configured" is a false statement about a Go repo — it is
    # a statement about a Python linter nobody asked for.
    _write_go_project(tmp_path)

    inventory = build_plan(tmp_path).inventory

    assert all("not a Python project" in c.detail for c in inventory.capabilities)


def test_an_empty_directory_is_treated_as_non_python(tmp_path):
    plan = build_plan(tmp_path, answers={"rigor.tier": "production"})

    assert not [
        a for a in plan.actions
        if a.path in ("ruff.toml", "pytest.ini", "mypy.ini")
    ]
    assert not [q for q in plan.questions.questions if q.id.startswith("adopt.")]


def test_a_non_python_project_can_still_record_its_rigor_tier(tmp_path):
    # The complement of the two tests above: language-agnostic decisions
    # must remain available to projects the Python scaffolds do not fit.
    plan = build_plan(tmp_path, answers={"rigor.tier": "production"})

    assert [a for a in plan.actions if a.path == ".agentharness-profile"]


def test_a_python_project_is_unaffected(tmp_path):
    _write(tmp_path, "pyproject.toml", '[project]\nname = "demo"\n')

    ids = {q.id for q in build_plan(tmp_path).questions.questions}

    assert "adopt.lint" in ids


# ---------------------------------------------------------------------------
# The two baseline decisions have to survive the run that asks them.
#
# rigor.tier and authority.publish were asked, blocked plan resolution, and
# were then discarded: neither produced an action, nothing reached disk, and
# the next `bootstrap plan` asked again. The interview could never converge.
# Found running the published npm package against a fresh project.
# ---------------------------------------------------------------------------

_BASELINE = {"rigor.tier": "production", "authority.publish": "stage"}


def _py(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "w"\nversion = "0.1.0"\n', encoding="utf-8"
    )


def test_rigor_tier_answer_produces_a_file_to_write(tmp_path):
    _py(tmp_path)
    plan = build_plan(tmp_path, answers=dict(_BASELINE))

    profile = [a for a in plan.actions if a.path == ".agentharness-profile"]
    assert profile, "the chosen rigor tier was discarded"
    assert profile[0].content.strip() == "production"


def test_an_existing_profile_answers_the_question(tmp_path):
    # Convergence: a settled decision must not be re-asked forever.
    _py(tmp_path)
    (tmp_path / ".agentharness-profile").write_text("prototype\n", encoding="utf-8")

    plan = build_plan(tmp_path)

    assert plan.answers.get("rigor.tier") == "prototype"
    assert not [a for a in plan.actions if a.path == ".agentharness-profile"]


def test_an_explicit_answer_overrides_what_is_on_disk(tmp_path):
    # Reading from disk must not make a decision unchangeable.
    #
    # The first cut of this test asserted only that the ANSWER changed,
    # which it did — while no action was produced, so the file kept its
    # old tier and nothing actually changed. Asserting the outcome, not
    # the intermediate state, is what makes this test mean anything.
    _py(tmp_path)
    (tmp_path / ".agentharness-profile").write_text("prototype\n", encoding="utf-8")

    plan = build_plan(tmp_path, answers={"rigor.tier": "production"})

    assert plan.answers["rigor.tier"] == "production"
    profile = [a for a in plan.actions if a.path == ".agentharness-profile"]
    assert profile, "the tier could be answered but never actually changed"
    assert profile[0].content.strip() == "production"
    assert profile[0].overwrite


def test_a_malformed_profile_can_be_repaired(tmp_path):
    # Keying the action on existence alone meant a corrupt profile was
    # permanent: the question re-opened, the answer was accepted, the plan
    # resolved, and no action was ever proposed to fix the file.
    _py(tmp_path)
    (tmp_path / ".agentharness-profile").write_text("banana\n", encoding="utf-8")

    plan = build_plan(tmp_path, answers={"rigor.tier": "production"})

    profile = [a for a in plan.actions if a.path == ".agentharness-profile"]
    assert profile
    assert "banana" in profile[0].rationale  # says what it is replacing


def test_a_profile_that_already_matches_proposes_nothing(tmp_path):
    # The complement: convergence must survive the overwrite path.
    _py(tmp_path)
    (tmp_path / ".agentharness-profile").write_text("production\n", encoding="utf-8")

    plan = build_plan(tmp_path, answers={"rigor.tier": "production"})

    assert not [a for a in plan.actions if a.path == ".agentharness-profile"]


def test_scaffolds_never_overwrite(tmp_path):
    # The overwrite exemption is for harness-owned decision files only.
    # An unrecognised ruff.toml must still be left alone.
    _py(tmp_path)
    plan = build_plan(
        tmp_path, answers={**_BASELINE, "adopt.lint": "yes"}
    )
    lint = [a for a in plan.actions if a.path == "ruff.toml"]
    assert lint
    assert not lint[0].overwrite


def test_publish_grant_is_written_only_when_granted(tmp_path):
    _py(tmp_path)

    granted = build_plan(
        tmp_path, answers={**_BASELINE, "authority.publish": "publish"}
    )
    staged = build_plan(tmp_path, answers=dict(_BASELINE))

    assert [a for a in granted.actions if a.path == ".agentharness-publish-mode"]
    # 'stage' is the safe default and is represented by the flag's ABSENCE:
    # answering it must never create the file that grants authority.
    assert not [a for a in staged.actions if a.path == ".agentharness-publish-mode"]


def test_an_existing_publish_flag_answers_the_question(tmp_path):
    _py(tmp_path)
    (tmp_path / ".agentharness-publish-mode").touch()

    plan = build_plan(tmp_path)

    assert plan.answers.get("authority.publish") == "publish"


def test_an_invalid_rigor_tier_is_rejected(tmp_path):
    # The answer is now written to a file enforce-profile reads, so an
    # unvalidated value would produce a config no tool can interpret.
    _py(tmp_path)
    with pytest.raises(ValueError, match="invalid value for rigor.tier"):
        build_plan(tmp_path, answers={"rigor.tier": "banana"})


def test_an_invalid_publish_answer_is_rejected(tmp_path):
    _py(tmp_path)
    with pytest.raises(ValueError, match="invalid value for authority.publish"):
        build_plan(tmp_path, answers={"authority.publish": "sometimes"})


def test_a_malformed_profile_on_disk_does_not_answer_the_question(tmp_path):
    # A corrupt file must re-open the question, not silently adopt junk.
    _py(tmp_path)
    (tmp_path / ".agentharness-profile").write_text("banana\n", encoding="utf-8")

    plan = build_plan(tmp_path)

    assert "rigor.tier" not in plan.answers


# ---------------------------------------------------------------------------
# Answering "stage" is a decision and has to be recorded.
#
# The safe default is the ABSENCE of a publish grant, so nothing on disk
# distinguished "chose to stage" from "never asked" and the question was
# re-asked on every run while rigor.tier converged. Recorded now as an
# explicit contract using the scoped-authority mechanism that already
# exists, rather than inventing a new file type.
# ---------------------------------------------------------------------------


def test_stage_is_recorded_as_an_explicit_contract(tmp_path):
    _py(tmp_path)
    plan = build_plan(tmp_path, answers={**_BASELINE, "authority.publish": "stage"})

    contract = [a for a in plan.actions if a.path == ".agentharness-authority.json"]
    assert contract, "answering 'stage' recorded nothing, so it is asked forever"


def test_the_stage_contract_denies_publishing(tmp_path):
    # The whole point: it must grant local commits and withhold push and
    # pr-create. Checked through the real loader and decider, not by
    # reading the JSON — a contract that merely parses is not enough.
    from agentharness.authority.loader import load_contract_text
    from agentharness.authority.operations import decide

    _py(tmp_path)
    plan = build_plan(tmp_path, answers={**_BASELINE, "authority.publish": "stage"})
    action = next(
        a for a in plan.actions if a.path == ".agentharness-authority.json"
    )

    contract = load_contract_text(action.content)

    assert decide(contract, "commit").allowed
    assert not decide(contract, "push").allowed
    assert not decide(contract, "pr-create").allowed
    assert not decide(contract, "pr-merge").allowed


def test_a_stage_contract_answers_the_question(tmp_path):
    _py(tmp_path)
    plan = build_plan(tmp_path, answers={**_BASELINE, "authority.publish": "stage"})
    action = next(
        a for a in plan.actions if a.path == ".agentharness-authority.json"
    )
    (tmp_path / ".agentharness-authority.json").write_text(
        action.content, encoding="utf-8"
    )

    reread = build_plan(tmp_path)

    assert reread.answers.get("authority.publish") == "stage"
    assert not [
        a for a in reread.actions if a.path == ".agentharness-authority.json"
    ]


def test_a_contract_granting_push_reads_back_as_publish(tmp_path):
    _py(tmp_path)
    (tmp_path / ".agentharness-authority.json").write_text(
        json.dumps({
            "schema_version": 1,
            "grants": [{"operations": ["commit", "push", "pr-create"]}],
            "revoked": [],
        }),
        encoding="utf-8",
    )

    assert build_plan(tmp_path).answers.get("authority.publish") == "publish"


def test_the_contract_outranks_the_publish_flag(tmp_path):
    # CLAUDE.md's precedence: contract > bare flag. Reading the flag first
    # would report authority the contract actually withholds — and this is
    # the contradiction the flag alone could not resolve.
    _py(tmp_path)
    (tmp_path / ".agentharness-publish-mode").touch()
    (tmp_path / ".agentharness-authority.json").write_text(
        json.dumps({
            "schema_version": 1,
            "grants": [{"operations": ["commit"]}],
            "revoked": [],
        }),
        encoding="utf-8",
    )

    assert build_plan(tmp_path).answers.get("authority.publish") == "stage"


def test_an_existing_contract_is_never_overwritten(tmp_path):
    # It may carry grants an operator wrote by hand; rewriting it to
    # commit-only would silently discard them.
    _py(tmp_path)
    (tmp_path / ".agentharness-authority.json").write_text(
        json.dumps({
            "schema_version": 1,
            "grants": [{"operations": ["commit", "push"], "target": "fix/*"}],
            "revoked": [],
        }),
        encoding="utf-8",
    )

    plan = build_plan(tmp_path, answers={"authority.publish": "stage"})

    assert not [
        a for a in plan.actions if a.path == ".agentharness-authority.json"
    ]


def test_an_unreadable_contract_reopens_the_question(tmp_path):
    # An unparseable file must never be treated as a decision, and least
    # of all as a grant.
    _py(tmp_path)
    (tmp_path / ".agentharness-authority.json").write_text("{ broken", encoding="utf-8")

    assert "authority.publish" not in build_plan(tmp_path).answers


def test_answering_publish_still_writes_the_flag(tmp_path):
    # Unchanged behaviour: 'publish' keeps using the documented flag.
    _py(tmp_path)
    plan = build_plan(tmp_path, answers={**_BASELINE, "authority.publish": "publish"})

    paths = {a.path for a in plan.actions}
    assert ".agentharness-publish-mode" in paths
    assert ".agentharness-authority.json" not in paths
