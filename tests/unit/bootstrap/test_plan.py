"""Tests for the bootstrap plan composer.

A plan is the contract between discovery and apply. It must be
deterministic (same repo + same answers => same hash), it must never
propose changing something the repo already has, and it must stay
unresolved until every question has an answer — apply is gated on that.
"""

from __future__ import annotations

from pathlib import Path

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

    assert plan.actions == ()
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

    assert plan.actions == ()
    assert not [q for q in plan.questions.questions if q.id.startswith("adopt.")]


def test_a_python_project_is_unaffected(tmp_path):
    _write(tmp_path, "pyproject.toml", '[project]\nname = "demo"\n')

    ids = {q.id for q in build_plan(tmp_path).questions.questions}

    assert "adopt.lint" in ids
