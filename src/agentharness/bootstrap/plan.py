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
    """One file the plan would create, and why."""

    capability: str
    path: str
    summary: str
    rationale: str

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

    actions: list[PlanAction] = []
    for capability in inventory.absent:
        if capability not in _SCAFFOLDS:
            continue
        if supplied.get(f"adopt.{capability}", "").strip().lower() not in _AFFIRMATIVE:
            continue
        rel_path, _ = _SCAFFOLDS[capability]
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
            )
        )

    return BootstrapPlan(
        inventory=inventory,
        questions=question_set,
        actions=tuple(actions),
        answers=supplied,
    )
