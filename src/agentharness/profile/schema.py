from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProfileError(ValueError):
    """A stable, operator-safe profile validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class Gate(StrEnum):
    COMMIT = "commit"
    PUSH = "push"
    CI = "ci"
    COMPLETION = "completion"


class BootstrapMode(StrEnum):
    STRICT = "strict"
    GRACE = "grace"
    WARN = "warn"


type FrozenScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class FrozenSequence:
    items: tuple[FrozenValue, ...]


@dataclass(frozen=True, slots=True)
class FrozenMapping:
    entries: tuple[tuple[str, FrozenValue], ...]


type FrozenValue = FrozenScalar | FrozenSequence | FrozenMapping


@dataclass(frozen=True, slots=True)
class Runtime:
    lock: str


@dataclass(frozen=True, slots=True)
class Project:
    name: str
    rigor: str


@dataclass(frozen=True, slots=True)
class Bootstrap:
    mode: BootstrapMode
    confirmed_at: str
    existing_checks_are_required: bool


@dataclass(frozen=True, slots=True)
class Plugin:
    identifier: str
    enabled: bool
    version: str
    config: FrozenMapping


@dataclass(frozen=True, slots=True)
class Scope:
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Requirement:
    identifier: str
    provider: str
    enabled: bool
    gates: tuple[Gate, ...]
    tool: str | None = None
    command: tuple[str, ...] = ()
    standard: str | None = None
    checks: tuple[str, ...] = ()
    minimum_coverage: int | None = None
    minimum_score: int | None = None
    required_for: tuple[str, ...] = ()
    scope: Scope = Scope()


@dataclass(frozen=True, slots=True)
class ReviewSignal:
    type: str
    name: str
    allowed_conclusions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Reviews:
    expected_signals: tuple[ReviewSignal, ...]
    timeout_seconds: int
    stabilization_seconds: int


@dataclass(frozen=True, slots=True)
class Completion:
    require_clean_tree: bool
    require_committed_changes: bool
    publication: str
    require_current_ci: bool
    require_resolved_reviews: bool


@dataclass(frozen=True, slots=True)
class Workflow:
    reviews: Reviews
    completion: Completion


@dataclass(frozen=True, slots=True)
class RequirementReductionProtection:
    codeowners: tuple[str, ...]
    require_codeowner_approval: bool
    minimum_total_approvals: int


@dataclass(frozen=True, slots=True)
class WaiverProtection:
    require_expiry: bool
    require_reason: bool


@dataclass(frozen=True, slots=True)
class Protection:
    provider: str
    default_branch: str
    requirement_reductions: RequirementReductionProtection
    waivers: WaiverProtection


@dataclass(frozen=True, slots=True)
class Profile:
    schema_version: int
    runtime: Runtime
    project: Project
    bootstrap: Bootstrap
    plugins: tuple[Plugin, ...]
    requirements: tuple[Requirement, ...]
    workflow: Workflow
    protection: Protection


@dataclass(frozen=True, slots=True)
class PresentationOverride:
    output_format: str | None = None
    color: str | None = None


@dataclass(frozen=True, slots=True)
class PerformanceOverride:
    concurrency: int | None = None
    timeout_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class LocalOverride:
    schema_version: int
    presentation: PresentationOverride = PresentationOverride()
    performance: PerformanceOverride = PerformanceOverride()
