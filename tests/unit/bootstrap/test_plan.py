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


def test_empty_project_asks_the_baseline_questions(tmp_path):
    plan = build_plan(tmp_path)
    ids = {q.id for q in plan.questions.questions}

    assert "rigor.tier" in ids
    assert "authority.publish" in ids


def test_absent_capabilities_become_adoption_questions(tmp_path):
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
    plan = build_plan(tmp_path, answers={"adopt.lint": "yes"})

    assert any(a.capability == "lint" for a in plan.actions)


def test_answering_no_produces_no_action_for_that_capability(tmp_path):
    plan = build_plan(tmp_path, answers={"adopt.lint": "no"})

    assert all(a.capability != "lint" for a in plan.actions)


def test_hash_is_stable_across_identical_builds(tmp_path):
    answers = {"adopt.lint": "yes", "rigor.tier": "production"}

    first = build_plan(tmp_path, answers=answers)
    second = build_plan(tmp_path, answers=answers)

    assert first.plan_hash == second.plan_hash


def test_hash_changes_when_an_answer_changes(tmp_path):
    # apply --confirm <hash> relies on this: a plan the owner did not see
    # must not pass confirmation.
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
