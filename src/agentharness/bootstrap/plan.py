"""Bootstrap plan composition.

Turns a read-only repository inventory plus the owner's answers into a
deterministic, hashable plan of what would change. This is the contract
between discovery and apply:

*Preserve what exists.* A capability the repository already configures is
never offered for adoption and never generates an action. Bootstrap adds
what is missing; it does not relitigate working setups.

*Nothing happens without an answer.* Every absent capability becomes an
explicit question. A plan stays unresolved until all of them are
answered, and apply refuses an unresolved plan — so no file is ever
created because the owner failed to say no.

*The hash covers everything the owner saw.* Inventory, answers, and
actions all feed the plan hash, so `apply --confirm <hash>` rejects a
plan that has drifted since it was presented.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentharness.bootstrap.discovery import (
    CAPABILITY_LABELS,
    NOT_PYTHON_DETAIL,
    RepoInventory,
    discover,
)
from agentharness.bootstrap.questions import Question, QuestionSet

# Baseline questions asked of every project, independent of what was
# detected. These are the "how should the harness behave here" decisions
# the owner alone can make.
BASELINE_QUESTIONS: tuple[Question, ...] = (
    Question(
        id="rigor.tier",
        prompt=(
            "Which rigor tier applies to this project? "
            "'prototype' relaxes coverage and review requirements; "
            "'production' enforces the full mandate."
        ),
        default="production",
    ),
    Question(
        id="authority.publish",
        prompt=(
            "Should agents publish autonomously? "
            "'stage' means verify and stage locally, then stop for your "
            "confirmation; 'publish' grants push/PR authority."
        ),
        default="stage",
    ),
)

# What gets scaffolded when the owner adopts a missing capability. Paths
# are relative to the project root; content is deliberately minimal —
# a starting point the owner edits, not an opinionated config dump.
_SCAFFOLDS: dict[str, tuple[str, str]] = {
    "lint": (
        "ruff.toml",
        '# Added by agentharness bootstrap. Adjust to taste.\nline-length = 88\n'
        '\n[lint]\nselect = ["E", "F", "I", "UP"]\n',
    ),
    "test": (
        "pytest.ini",
        # Section header must be [tool:pytest] — that is what pytest reads
        # from a standalone pytest.ini/setup.cfg, and what detection keys
        # on. A [pytest] header would create a file neither pytest nor the
        # next discovery run recognises.
        "# Added by agentharness bootstrap. Adjust to taste.\n"
        "[tool:pytest]\ntestpaths = tests\n",
    ),
    "types": (
        "mypy.ini",
        "# Added by agentharness bootstrap. Adjust to taste.\n"
        "[mypy]\nstrict = True\n",
    ),
}

_AFFIRMATIVE = {"yes", "y", "true", "1"}


@dataclass(frozen=True)
class PlanAction:
    """One file the plan would create, and why.

    `content` travels with the action rather than being looked up by
    capability at write time. The lookup form could only express files
    that map to a scaffolded capability, which is why the two baseline
    decisions — rigor tier and publish authority — produced no action at
    all: they were asked, they blocked resolution, and then they were
    discarded. It is deliberately not part of `to_dict`; the JSON
    contract describes what will change and why, not file bodies.
    """

    capability: str
    path: str
    summary: str
    rationale: str
    content: str = ""
    # Whether this action may replace a file that already exists. Scaffolds
    # never may — discovery only recognises config it knows, so an
    # unrecognised file at the same path would be silently clobbered. The
    # harness's own decision files are different: they have a known, tiny
    # format that the harness itself owns, and refusing to rewrite them
    # made a recorded decision permanent — a malformed profile could not
    # be repaired and a chosen tier could not be changed.
    overwrite: bool = False

    def to_dict(self) -> dict[str, str]:
        return {
            "capability": self.capability,
            "path": self.path,
            "summary": self.summary,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class BootstrapPlan:
    """A deterministic, hashable description of a proposed first run."""

    inventory: RepoInventory
    questions: QuestionSet
    actions: tuple[PlanAction, ...]
    answers: dict[str, str] = field(default_factory=dict)

    @property
    def is_resolved(self) -> bool:
        """True when every question has an answer. apply requires this."""
        return self.questions.is_resolved

    @property
    def plan_hash(self) -> str:
        """Stable digest of everything the owner was shown."""
        payload = json.dumps(self._hashable(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _hashable(self) -> dict[str, Any]:
        return {
            "capabilities": [
                {
                    "capability": c.capability,
                    "present": c.present,
                    "detail": c.detail,
                    "evidence": list(c.evidence),
                }
                for c in self.inventory.capabilities
            ],
            "answers": dict(sorted(self.answers.items())),
            "actions": [a.to_dict() for a in self.actions],
        }

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe representation — the CLI's --json output."""
        return {
            "root": self.inventory.root,
            "detected": [
                {
                    "capability": c.capability,
                    "label": CAPABILITY_LABELS.get(c.capability, c.capability),
                    "present": c.present,
                    "detail": c.detail,
                    "evidence": list(c.evidence),
                }
                for c in self.inventory.capabilities
            ],
            "questions": [
                {
                    "id": q.id,
                    "prompt": q.prompt,
                    "default": q.default,
                    "answered": self.answers.get(q.id),
                }
                for q in self.questions.questions
            ],
            "actions": [a.to_dict() for a in self.actions],
            "is_resolved": self.is_resolved,
            "plan_hash": self.plan_hash,
        }


# Where the two baseline decisions are recorded, and what a valid answer
# to each one is. These files are what the rest of the harness actually
# reads: enforce-profile reads .agentharness-profile, and publish
# authority resolves against .agentharness-publish-mode.
PROFILE_PATH = ".agentharness-profile"
PUBLISH_MODE_PATH = ".agentharness-publish-mode"

# The tiers that exist as patterns/profiles/*.yaml. Validated because the
# answer is now written to disk: an unvalidated value produced a
# .agentharness-profile that enforce-profile could not read.
VALID_TIERS: tuple[str, ...] = ("prototype", "production", "internal")
VALID_PUBLISH: tuple[str, ...] = ("stage", "publish")

_BASELINE_VALID: dict[str, tuple[str, ...]] = {
    "rigor.tier": VALID_TIERS,
    "authority.publish": VALID_PUBLISH,
}


def _validate_baseline(supplied: dict[str, str]) -> None:
    """Reject a baseline answer that is not one of the allowed values.

    Previously any string was accepted, because nothing consumed it.
    Now that these answers are written to files the harness reads, a
    typo would produce a config no tool can interpret.
    """
    for key, allowed in _BASELINE_VALID.items():
        value = supplied.get(key)
        if value is None:
            continue
        if value.strip().lower() not in allowed:
            raise ValueError(
                f"invalid value for {key}: {value!r} — "
                f"valid values are: {', '.join(allowed)}"
            )


def _answers_from_disk(root: Path, supplied: dict[str, str]) -> dict[str, str]:
    """Pre-answer baseline questions already settled on disk.

    Without this the interview never converges: a project that had been
    bootstrapped was asked the same two questions on every subsequent
    run, because the answers were only ever held in argv. An explicit
    --answer still wins, so a run can change a decision.
    """
    resolved = dict(supplied)

    profile = root / PROFILE_PATH
    if "rigor.tier" not in resolved and profile.is_file():
        existing = profile.read_text(encoding="utf-8", errors="replace").strip()
        if existing.lower() in VALID_TIERS:
            resolved["rigor.tier"] = existing.lower()

    if "authority.publish" not in resolved and (root / PUBLISH_MODE_PATH).exists():
        # The flag's presence IS the grant, so its presence is the answer.
        resolved["authority.publish"] = "publish"

    return resolved


def _decision_actions(root: Path, supplied: dict[str, str]) -> list[PlanAction]:
    """Files that record the baseline decisions."""
    actions: list[PlanAction] = []

    tier = supplied.get("rigor.tier", "").strip().lower()
    if tier:
        profile = root / PROFILE_PATH
        current = (
            profile.read_text(encoding="utf-8", errors="replace").strip().lower()
            if profile.is_file()
            else None
        )
        # Propose a write whenever the file does not already say what was
        # chosen. Keying only on existence meant a malformed profile could
        # never be repaired and an existing tier could never be changed:
        # the answer was accepted, the plan resolved, and nothing happened.
        if current != tier:
            verb = "Update" if current is not None else "Create"
            rationale = (
                f"You chose the {tier} rigor tier; this is the file "
                f"enforce-profile reads to apply it."
            )
            if current is not None:
                rationale = (
                    f"{rationale} The file currently reads {current!r}."
                )
            actions.append(
                PlanAction(
                    capability="rigor",
                    path=PROFILE_PATH,
                    summary=f"{verb} {PROFILE_PATH} ({tier})",
                    rationale=rationale,
                    content=f"{tier}\n",
                    overwrite=True,
                )
            )

    publish = supplied.get("authority.publish", "").strip().lower()
    if publish == "publish" and not (root / PUBLISH_MODE_PATH).exists():
        actions.append(
            PlanAction(
                capability="authority",
                path=PUBLISH_MODE_PATH,
                summary=f"Create {PUBLISH_MODE_PATH}",
                rationale=(
                    "You granted agents standing authority to push and open "
                    "PRs. Delete this file to revoke it."
                ),
                # Empty, matching the `touch` the docs describe: the flag's
                # presence is the grant, and nothing reads its contents.
                content="",
            )
        )

    return actions


def _adoption_questions(inventory: RepoInventory) -> tuple[Question, ...]:
    """One question per absent capability that we can actually scaffold."""
    # Nothing to adopt when the scaffolds do not apply to this project.
    if any(c.detail == NOT_PYTHON_DETAIL for c in inventory.capabilities):
        return ()
    return tuple(
        Question(
            id=f"adopt.{capability}",
            prompt=(
                f"{CAPABILITY_LABELS.get(capability, capability)} is not "
                f"configured. Add a starter configuration? (yes/no)"
            ),
            default="yes",
        )
        for capability in inventory.absent
        if capability in _SCAFFOLDS
    )


def build_plan(
    root: Path | str,
    answers: dict[str, str] | None = None,
) -> BootstrapPlan:
    """Compose a plan for `root`, incorporating any answers supplied so far.

    Raises ValueError for an answer key that matches no question — a
    typo'd `--answer` must fail loudly rather than silently leaving the
    plan unresolved for an unexplained reason.
    """
    root_path = Path(root)
    supplied = dict(answers or {})
    _validate_baseline(supplied)
    supplied = _answers_from_disk(root_path, supplied)
    inventory = discover(root_path)

    questions = BASELINE_QUESTIONS + _adoption_questions(inventory)
    known = {q.id for q in questions}
    unknown = sorted(set(supplied) - known)
    if unknown:
        raise ValueError(
            f"unknown answer key(s): {', '.join(unknown)} — "
            f"valid keys are: {', '.join(sorted(known))}"
        )

    question_set = QuestionSet(questions=list(questions))
    for question in questions:
        if question.id in supplied:
            question_set = question_set.answer(question, supplied[question.id])

    actions: list[PlanAction] = _decision_actions(root_path, supplied)
    for capability in inventory.absent:
        if capability not in _SCAFFOLDS:
            continue
        if supplied.get(f"adopt.{capability}", "").strip().lower() not in _AFFIRMATIVE:
            continue
        rel_path, scaffold_content = _SCAFFOLDS[capability]
        # Never propose overwriting something already on disk. Discovery
        # only reads config it recognises, so an unrecognised file at the
        # same path would otherwise be silently clobbered.
        if (root_path / rel_path).exists():
            continue
        actions.append(
            PlanAction(
                capability=capability,
                path=rel_path,
                summary=f"Create {rel_path}",
                rationale=(
                    f"{CAPABILITY_LABELS.get(capability, capability)} was not "
                    f"detected and you asked to adopt it."
                ),
                content=scaffold_content,
            )
        )

    return BootstrapPlan(
        inventory=inventory,
        questions=question_set,
        actions=tuple(actions),
        answers=supplied,
    )
