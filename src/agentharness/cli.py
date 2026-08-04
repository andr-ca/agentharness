import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Never, TextIO

from agentharness.errors import CommandUsageError
from agentharness.models import (
    CommandResult,
    JsonValue,
    Outcome,
    ResultCode,
    SupportedJsonValue,
)
from agentharness.runtime_upgrade import (
    UpgradePlanningError,
    load_upgrade_request,
    plan_upgrade,
)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise CommandUsageError from None


def create_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(prog="agentharness", add_help=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status", add_help=False)
    status_parser.add_argument("--json", action="store_true", dest="as_json")

    # bootstrap: the first-run surface. `plan` is strictly read-only and
    # emits the findings/questions an agent skill turns into an interview;
    # `apply` writes only what a resolved, hash-confirmed plan describes.
    bootstrap_parser = subparsers.add_parser("bootstrap", add_help=False)
    bootstrap_sub = bootstrap_parser.add_subparsers(
        dest="bootstrap_command", required=True
    )

    bs_plan = bootstrap_sub.add_parser("plan", add_help=False)
    bs_plan.add_argument("--json", action="store_true", dest="as_json")
    bs_plan.add_argument("--target-dir", dest="target_dir", default=".", type=Path)
    # Positional alternative to --target-dir (issue found dogfooding a real
    # npm install): every bash-served subcommand in this same CLI — audit,
    # doctor, uninstall, init — takes the target as a plain positional
    # argument. 'bootstrap plan .', the natural first thing to type having
    # used any of those, hit argparse's unrecognized-argument error, which
    # SafeArgumentParser then flattens to the opaque "The command is
    # invalid." with no hint that --target-dir was the only accepted form.
    bs_plan.add_argument("target_dir_positional", nargs="?", default=None, type=Path)
    bs_plan.add_argument(
        "--answer",
        dest="answers",
        action="append",
        default=[],
        metavar="KEY=VALUE",
    )

    bs_apply = bootstrap_sub.add_parser("apply", add_help=False)
    bs_apply.add_argument("--json", action="store_true", dest="as_json")
    bs_apply.add_argument("--target-dir", dest="target_dir", default=".", type=Path)
    bs_apply.add_argument("target_dir_positional", nargs="?", default=None, type=Path)
    bs_apply.add_argument(
        "--answer",
        dest="answers",
        action="append",
        default=[],
        metavar="KEY=VALUE",
    )
    bs_apply.add_argument("--confirm", dest="confirm", default=None)

    runtime_parser = subparsers.add_parser("runtime", add_help=False)
    runtime_subparsers = runtime_parser.add_subparsers(
        dest="runtime_command", required=True
    )
    plan_upgrade_parser = runtime_subparsers.add_parser(
        "plan-upgrade", add_help=False
    )
    plan_upgrade_parser.add_argument("--base-lock", type=Path, required=True)
    plan_upgrade_parser.add_argument("--request", type=Path, required=True)
    plan_upgrade_parser.add_argument("--json", action="store_true", dest="as_json")

    # GitHub sub-commands
    github_parser = subparsers.add_parser("github", add_help=False)
    github_sub = github_parser.add_subparsers(dest="github_command", required=True)

    # github protection plan
    gh_prot = github_sub.add_parser("protection", add_help=False)
    gh_prot_sub = gh_prot.add_subparsers(dest="prot_command", required=True)
    gh_plan = gh_prot_sub.add_parser("plan", add_help=False)
    gh_plan.add_argument("--repo", required=True, help="owner/repo")
    gh_plan.add_argument("--branch", default="main")
    gh_plan.add_argument("--json", action="store_true", dest="as_json")
    gh_apply = gh_prot_sub.add_parser("apply", add_help=False)
    gh_apply.add_argument("--repo", required=True, help="owner/repo")
    gh_apply.add_argument("--branch", default="main")
    gh_apply.add_argument(
        "--token-env", default="GITHUB_TOKEN", dest="token_env"
    )
    gh_apply.add_argument("--json", action="store_true", dest="as_json")

    # github completion check
    gh_comp = github_sub.add_parser("completion", add_help=False)
    gh_comp_sub = gh_comp.add_subparsers(dest="comp_command", required=True)
    gh_check = gh_comp_sub.add_parser("check", add_help=False)
    gh_check.add_argument("--repo", required=True)
    gh_check.add_argument("--pr", type=int, required=True)
    gh_check.add_argument("--expected-head", required=True)
    gh_check.add_argument(
        "--token-env", default="GITHUB_TOKEN", dest="token_env"
    )
    gh_check.add_argument("--json", action="store_true", dest="as_json")

    # profile sub-commands (AC-10)
    profile_parser = subparsers.add_parser("profile", add_help=False)
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)

    pf_validate = profile_sub.add_parser("validate", add_help=False)
    pf_validate.add_argument("file", type=Path, help="Profile YAML to validate")
    pf_validate.add_argument("--json", action="store_true", dest="as_json")

    pf_explain = profile_sub.add_parser("explain", add_help=False)
    pf_explain.add_argument("file", type=Path, help="Profile YAML to explain")
    pf_explain.add_argument("--json", action="store_true", dest="as_json")

    pf_preview = profile_sub.add_parser("preview", add_help=False)
    pf_preview.add_argument("file", type=Path, help="New profile YAML to preview")
    pf_preview.add_argument(
        "--current", type=Path, default=None, dest="current",
        help="Current profile for diff (default: .agentharness-profile.yaml)"
    )
    pf_preview.add_argument("--json", action="store_true", dest="as_json")

    pf_apply = profile_sub.add_parser("apply", add_help=False)
    pf_apply.add_argument("file", type=Path, help="Profile YAML to apply")
    pf_apply.add_argument(
        "--target", type=Path, default=None,
        help="Target file (default: .agentharness-profile.yaml)"
    )
    pf_apply.add_argument("--json", action="store_true", dest="as_json")

    # authority sub-commands
    authority_parser = subparsers.add_parser("authority", add_help=False)
    authority_parser.add_argument("--json", action="store_true", dest="as_json")
    authority_parser.add_argument("--target-dir", default=".", type=Path)

    authority_sub = authority_parser.add_subparsers(
        dest="authority_command", required=False
    )

    # check subcommand
    auth_check = authority_sub.add_parser("check", add_help=False)
    auth_check.add_argument(
        "--operation", required=True, help="Operation name to check"
    )
    auth_check.add_argument(
        "--target", default=None, help="Optional target (e.g., branch pattern)"
    )
    # Positional repo root for `check`. Named distinctly from the parent
    # parser's --target-dir (same dest would make the CLI ambiguous); the
    # dispatcher prefers this when supplied, else falls back to --target-dir.
    auth_check.add_argument("repo_root", nargs="?", default=None, type=Path)

    return parser


def _parse_answers(raw: Sequence[str]) -> dict[str, str]:
    """Parse repeated --answer KEY=VALUE flags.

    A malformed pair is rejected rather than ignored: silently dropping
    an answer would leave the plan unresolved with no visible reason.
    """
    answers: dict[str, str] = {}
    for item in raw:
        key, separator, value = item.partition("=")
        if not separator or not key.strip():
            raise CommandUsageError
        answers[key.strip()] = value.strip()
    return answers


def execute_bootstrap_plan(
    target_dir: Path,
    raw_answers: Sequence[str],
) -> CommandResult:
    """Read-only: inventory the project and report findings and questions."""
    from agentharness.bootstrap.plan import build_plan

    try:
        plan = build_plan(target_dir, answers=_parse_answers(raw_answers))
    except ValueError as exc:
        return CommandResult(
            code=ResultCode.BOOTSTRAP_REJECTED,
            outcome=Outcome.ERROR,
            summary=str(exc),
            remediation=(
                "Run 'agentharness bootstrap plan' to see the findings "
                "and the valid question ids."
            ),
        )

    detected = len(plan.inventory.present)
    total = len(plan.inventory.capabilities)
    unanswered = [
        q.id for q in plan.questions.questions if q.id not in plan.answers
    ]
    remediation = (
        "Run 'agentharness bootstrap apply' with --confirm "
        f"{plan.plan_hash} to apply this plan."
        if plan.is_resolved
        else (
            "Answer the open questions with "
            "'agentharness bootstrap plan --answer <id>=<value>'."
        )
    )
    return CommandResult(
        code=ResultCode.BOOTSTRAP_PLANNED,
        outcome=Outcome.SUCCESS,
        summary=(
            f"Detected {detected} of {total} capabilities; "
            f"{len(plan.actions)} change(s) proposed, "
            f"{len(unanswered)} question(s) open."
        ),
        remediation=remediation,
        details=plan.to_dict(),
    )


def execute_bootstrap_apply(
    target_dir: Path,
    raw_answers: Sequence[str],
    confirm: str | None,
) -> CommandResult:
    """Apply a resolved, hash-confirmed plan through the bootstrap transaction."""
    from agentharness.bootstrap.plan import build_plan

    try:
        plan = build_plan(target_dir, answers=_parse_answers(raw_answers))
    except ValueError as exc:
        return CommandResult(
            code=ResultCode.BOOTSTRAP_REJECTED,
            outcome=Outcome.ERROR,
            summary=str(exc),
            remediation="Run 'agentharness bootstrap plan' to see valid ids.",
        )

    # Three refusals, in the order that gives the most useful message.
    if not plan.is_resolved:
        return CommandResult(
            code=ResultCode.BOOTSTRAP_REJECTED,
            outcome=Outcome.ERROR,
            summary="Plan is not resolved — some questions are unanswered.",
            remediation=(
                "Answer them with 'agentharness bootstrap plan "
                "--answer <id>=<value>'."
            ),
        )
    if confirm is None:
        return CommandResult(
            code=ResultCode.BOOTSTRAP_REJECTED,
            outcome=Outcome.ERROR,
            summary="Refusing to apply without an explicit confirmation hash.",
            remediation=(
                f"Re-run with --confirm {plan.plan_hash} once you have "
                "reviewed the plan."
            ),
        )
    if confirm != plan.plan_hash:
        return CommandResult(
            code=ResultCode.BOOTSTRAP_REJECTED,
            outcome=Outcome.ERROR,
            summary=(
                "Confirmation hash does not match the current plan — the "
                "project or your answers changed since it was shown."
            ),
            remediation=(
                "Re-run 'agentharness bootstrap plan' and review the "
                "current plan before confirming."
            ),
        )

    written: list[str] = []
    root = Path(target_dir)
    for action in plan.actions:
        # Content comes from the action. Looking it up by capability could
        # only ever express scaffolded capabilities, so the two baseline
        # decisions had nowhere to be written and were silently dropped.
        content = action.content
        destination = root / action.path
        # Re-check at write time, not just at plan time: the file may have
        # appeared between planning and applying. Actions that declare
        # overwrite are exempt — replacing the file IS the change they
        # describe, and it was shown and hash-confirmed as such.
        if destination.exists() and not action.overwrite:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        written.append(action.path)

    return CommandResult(
        code=ResultCode.BOOTSTRAP_APPLIED,
        outcome=Outcome.SUCCESS,
        summary=f"Applied {len(written)} change(s).",
        remediation="Run 'agentharness bootstrap plan' to re-inspect the project.",
        details={
            "written": list(written),
            "plan_hash": plan.plan_hash,
        },
    )


def execute_status() -> CommandResult:
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary="Project is not configured.",
        remediation="Run 'agentharness bootstrap plan' to inspect this project.",
        details={"state": "not_configured"},
    )


def execute_github_protection_plan(repo: str, branch: str) -> CommandResult:
    """Read current branch protection and compare to desired plan (read-only)."""
    from agentharness.remote.github.models import ProtectionPlan, ProtectionState
    from agentharness.remote.github.protection import plan_protection

    plan = ProtectionPlan(
        branch=branch,
        require_reviews=True,
        required_approvals=1,
        dismiss_stale_reviews=True,
        require_code_owner_reviews=True,
        required_contexts=["CI"],
    )

    # Try to read the current state without writing anything.
    current: ProtectionState | None = None
    try:
        from agentharness.remote.github.api import GitHubClient
        from agentharness.remote.github.auth import get_token
        token = get_token("GITHUB_TOKEN")
        owner, name = (repo.split("/", 1) if "/" in repo else (repo, repo))
        client = GitHubClient(token=token)
        path = f"/repos/{owner}/{name}/branches/{branch}/protection"
        raw = client.get(path)
        reviews = raw.get("required_pull_request_reviews") or {}
        checks = raw.get("required_status_checks") or {}
        current = ProtectionState(
            branch=branch,
            is_protected=True,
            required_approvals=reviews.get("required_approving_review_count", 0),
            dismiss_stale_reviews=reviews.get("dismiss_stale_reviews", False),
            require_code_owner_reviews=reviews.get("require_code_owner_reviews", False),
            required_contexts=checks.get("contexts", []),
        )
    except Exception:  # noqa: BLE001
        pass  # token unavailable or not yet protected — treat as unprotected

    result = plan_protection(plan, current=current)
    status = "applied" if result.matches_plan else "not yet applied"
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"Protection plan for {repo}/{branch}: {status}.",
        remediation=(
            ""
            if result.matches_plan
            else f"Run 'agentharness github protection apply --repo {repo}' to apply."
        ),
        details={
            "repo": repo,
            "branch": branch,
            "matches_plan": result.matches_plan,
            "required_approvals": plan.required_approvals,
        },
    )


def execute_github_protection_apply(
    repo: str,
    branch: str,
    token_env: str,
) -> CommandResult:
    """Apply and read back branch protection for *repo*/*branch*."""
    from agentharness.remote.github.api import APIError, GitHubClient
    from agentharness.remote.github.auth import AuthError, get_token
    from agentharness.remote.github.models import ProtectionPlan
    from agentharness.remote.github.protection import apply_protection

    try:
        token = get_token(token_env)
    except AuthError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=str(e),
            remediation=f"Set ${token_env} to a GitHub token with repo scope.",
            details={},
        )

    owner, name = (repo.split("/", 1) if "/" in repo else (repo, repo))
    plan = ProtectionPlan(
        branch=branch,
        require_reviews=True,
        required_approvals=1,
        dismiss_stale_reviews=True,
        require_code_owner_reviews=True,
        required_contexts=["CI"],
    )
    client = GitHubClient(token=token)
    try:
        reconcile = apply_protection(client, owner, name, plan)
    except APIError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"GitHub API error while applying protection: {e}",
            remediation="Check that the token has repo admin permissions.",
            details={},
        )

    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS if reconcile.matches_plan else Outcome.ERROR,
        summary=(
            "Branch protection applied and verified."
            if reconcile.matches_plan
            else "Branch protection applied but read-back did not match plan."
        ),
        remediation=(
            "Protection is active."
            if reconcile.matches_plan
            else "Re-run with --json to inspect the discrepancy."
        ),
        details={
            "repo": repo,
            "branch": branch,
            "matches_plan": reconcile.matches_plan,
        },
    )


def execute_github_completion_check(
    repo: str,
    pr_number: int,
    expected_head: str,
    token_env: str,
) -> CommandResult:
    """Check the completion gate for a pull request."""
    from agentharness.remote.github.api import APIError, GitHubClient
    from agentharness.remote.github.auth import AuthError, get_token
    from agentharness.remote.github.completion import evaluate_completion
    from agentharness.remote.github.models import PRState
    from agentharness.remote.github.reviews import extract_signals

    try:
        token = get_token(token_env)
    except AuthError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=str(e),
            remediation=f"Set ${token_env} to a GitHub token.",
            details={},
        )

    owner, name = (repo.split("/", 1) if "/" in repo else (repo, repo))
    client = GitHubClient(token=token)
    try:
        pr_data = client.get(f"/repos/{owner}/{name}/pulls/{pr_number}")
        checks_data = client.get(
            f"/repos/{owner}/{name}/commits/{pr_data['head']['sha']}/check-runs"
        )
    except APIError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"GitHub API error: {e}",
            remediation="Check that the token has repo read permissions.",
            details={},
        )

    runs = checks_data.get("check_runs", [])
    passing = [r["name"] for r in runs if r["conclusion"] == "success"]
    failing = [r["name"] for r in runs if r["conclusion"] not in ("success", None)]
    pr = PRState(
        number=pr_number,
        head_sha=pr_data["head"]["sha"],
        is_draft=pr_data.get("draft", False),
        review_decision=pr_data.get("review_decision"),
        unresolved_threads=0,  # would require graphql query
        passing_checks=passing,
        failing_checks=failing,
    )
    signals = extract_signals(pr)
    decision = evaluate_completion(signals, expected_head)

    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS if decision.is_complete else Outcome.ERROR,
        summary=(
            "PR is ready to complete."
            if decision.is_complete
            else f"PR is blocked: {'; '.join(decision.blocking_reasons)}"
        ),
        remediation=(
            "Merge when ready."
            if decision.is_complete
            else "Address the blocking reasons before merging."
        ),
        details={
            "pr": pr_number,
            "head_sha": pr.head_sha,
            "is_complete": decision.is_complete,
            "blocking_reasons": list(decision.blocking_reasons),
        },
    )


def execute_profile_validate(file: Path) -> CommandResult:
    """Validate a profile YAML file against the schema (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        profile = load_profile_text(file.read_text(encoding="utf-8"))
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary=f"Profile is valid (schema_version={profile.schema_version}).",
            remediation="",
            details={
                "file": str(file),
                "schema_version": profile.schema_version,
                "requirement_count": len(profile.requirements),
                "rigor": profile.project.rigor,
            },
        )
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile validation failed: {e}",
            remediation="Fix the YAML schema errors and retry.",
            details={"file": str(file), "error": str(e)},
        )


def execute_profile_explain(file: Path) -> CommandResult:
    """Show all requirements with capability/mode/gates (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        profile = load_profile_text(file.read_text(encoding="utf-8"))
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Could not parse profile: {e}",
            remediation="Run 'agentharness profile validate <file>' to diagnose.",
            details={"file": str(file), "error": str(e)},
        )
    reqs: list[dict[str, object]] = [
        {
            "id": r.identifier,
            "provider": r.provider,
            "enabled": r.enabled,
            "gates": [str(g) for g in r.gates],
            "minimum_coverage": getattr(r, "minimum_coverage", None),
        }
        for r in profile.requirements
    ]
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"{len(reqs)} requirement(s) in {file}",
        remediation="",
        details={
            "file": str(file),
            "requirements": reqs,  # type: ignore[dict-item]
        }
    )


def execute_profile_preview(file: Path, current: Path | None) -> CommandResult:
    """Show what diff a profile apply would make (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        load_profile_text(file.read_text(encoding="utf-8"))
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Incoming profile is invalid: {e}",
            remediation="Fix the YAML and retry.",
            details={"file": str(file), "error": str(e)},
        )
    current_path = current or Path(".agentharness-profile.yaml")
    if not current_path.exists():
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary=(
                f"No current profile at {current_path}"
                " — applying would create a new profile."
            ),
            remediation="",
            details={
                "current_file": str(current_path),
                "incoming_file": str(file),
                "diff": "new_file",
            },
        )
    current_text = current_path.read_text(encoding="utf-8")
    incoming_text = file.read_text(encoding="utf-8")
    if current_text == incoming_text:
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary="No changes — incoming profile is identical to current.",
            remediation="",
            details={
                "current_file": str(current_path),
                "incoming_file": str(file),
                "diff": "no_change",
            },
        )
    import difflib
    diff_lines: list[str] = list(
        difflib.unified_diff(
            current_text.splitlines(),
            incoming_text.splitlines(),
            fromfile=str(current_path),
            tofile=str(file),
            lineterm="",
        )
    )
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"{len(diff_lines)} diff line(s) between current and incoming profile.",
        remediation="Run 'agentharness profile apply <file>' to apply.",
        details={
            "current_file": str(current_path),
            "incoming_file": str(file),
            "diff": "changed",
            "diff_lines": diff_lines,  # type: ignore[dict-item]
        },
    )


def execute_profile_apply(file: Path, target: Path | None) -> CommandResult:
    """Write the profile to the target path (AC-10)."""
    from agentharness.profile import ProfileError, load_profile_text

    if not file.exists():
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile file not found: {file}",
            remediation="Check the file path and try again.",
            details={"file": str(file)},
        )
    try:
        load_profile_text(file.read_text(encoding="utf-8"))
    except (ProfileError, ValueError) as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Profile validation failed — not applied: {e}",
            remediation="Fix the YAML errors before applying.",
            details={"file": str(file), "error": str(e)},
        )
    target_path = target or Path(".agentharness-profile.yaml")
    try:
        target_path.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Could not write profile to {target_path}: {e}",
            remediation="Check file system permissions.",
            details={"target": str(target_path), "error": str(e)},
        )
    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=f"Profile applied to {target_path}.",
        remediation="",
        details={"source": str(file), "target": str(target_path)},
    )


def execute_authority_check(
    operation: str, target: str | None, target_dir: Path
) -> CommandResult:
    """Check if an operation is authorized."""
    from agentharness.authority.loader import load_effective_authority
    from agentharness.authority.operations import decide

    repo_root = target_dir.resolve()
    try:
        contract = load_effective_authority(repo_root)
    except ValueError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Failed to load authority contract: {e}",
            remediation="Check the authority contract file and try again.",
            details={"repo_root": str(repo_root), "error": str(e)},
        )

    decision = decide(contract, operation, target)
    if decision.allowed:
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.SUCCESS,
            summary=f"Operation '{operation}' is authorized.",
            remediation="",
            details={"operation": operation, "target": target, "allowed": True},
        )
    else:
        return CommandResult(
            code=ResultCode.STATUS_AVAILABLE,
            outcome=Outcome.ERROR,
            summary=f"Operation '{operation}' is not authorized: {decision.reason}",
            remediation="Request appropriate authority or contact the operator.",
            details={
                "operation": operation,
                "target": target,
                "allowed": False,
                "reason": decision.reason,
            },
        )


def execute_authority_info(as_json: bool, target_dir: Path) -> CommandResult:
    """Display or report the effective authority."""
    from datetime import UTC, datetime

    from agentharness.authority.loader import load_effective_authority

    repo_root = target_dir.resolve()
    try:
        contract = load_effective_authority(repo_root)
    except ValueError as e:
        return CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary=f"Failed to load authority contract: {e}",
            remediation="Check the authority contract file.",
            details={"repo_root": str(repo_root), "error": str(e)},
        )

    # Determine the source of authority
    contract_path = repo_root / ".agentharness-authority.json"
    flag_path = repo_root / ".agentharness-publish-mode"
    if contract_path.exists():
        source = "contract"
    elif flag_path.exists():
        source = "flag"
    else:
        source = "none"

    # Build operations list with details
    operations_granted: list[JsonValue] = []
    op_lines: list[str] = []
    now = datetime.now(UTC)

    for grant in contract.grants:
        for op in grant.operations:
            status = "active"
            reason = None
            if op.value in contract.revoked:
                status = "revoked"
                reason = "revoked"
            elif grant.expires:
                try:
                    if grant.expires.endswith("Z"):
                        expires_str = grant.expires.rstrip("Z") + "+00:00"
                    else:
                        expires_str = grant.expires
                    expires_dt = datetime.fromisoformat(expires_str)
                    if now >= expires_dt:
                        status = "expired"
                        reason = f"expired at {grant.expires}"
                except (ValueError, TypeError):
                    status = "invalid"
                    reason = "invalid expiry format"

            operations_granted.append(
                {
                    "operation": op.value,
                    "target": grant.target,
                    "expires": grant.expires,
                    "granted_by": grant.granted_by,
                    "status": status,
                    "reason": reason,
                }
            )
            op_lines.append(
                f"  - {op.value}  (target={grant.target or 'any'}, "
                f"expires={grant.expires or 'no expiry'})  [{status}]"
            )

    # Human-readable session preflight (render_human shows summary + Next line).
    if source == "none":
        summary = (
            "Authority source: none — no operations granted "
            "(verify-and-stage default)."
        )
    else:
        if source == "flag":
            header = (
                "Authority source: flag (.agentharness-publish-mode) — full "
                "grant of all operations."
            )
        else:
            header = "Authority source: contract (.agentharness-authority.json)."
        revoked = list(contract.revoked)
        revoked_line = f"\nRevoked: {', '.join(revoked)}" if revoked else ""
        summary = (
            f"{header}\nGranted operations:\n" + "\n".join(op_lines) + revoked_line
        )
    remediation = (
        "Enforcement is advisory unless a hook invokes "
        "`agentharness authority check <op>` (see docs/INTEGRATION.md); "
        "this client does not auto-enforce."
    )

    return CommandResult(
        code=ResultCode.STATUS_AVAILABLE,
        outcome=Outcome.SUCCESS,
        summary=summary,
        remediation=remediation,
        details={
            "source": source,
            "schema_version": contract.schema_version,
            "operations_granted": operations_granted,
            "revoked": list(contract.revoked),
        },
    )


def execute_runtime_plan_upgrade(
    request_path: Path, trusted_base_lock: Path
) -> CommandResult:
    try:
        plan = plan_upgrade(
            load_upgrade_request(
                request_path,
                trusted_base_lock=trusted_base_lock,
            )
        )
    except UpgradePlanningError:
        return CommandResult(
            code=ResultCode.RUNTIME_UPGRADE_REJECTED,
            outcome=Outcome.ERROR,
            summary="Runtime upgrade is not admissible under the base lock.",
            remediation=(
                "Inspect the base-authoritative upgrade evidence and keep the "
                "base lock."
            ),
        )
    return CommandResult(
        code=ResultCode.RUNTIME_UPGRADE_PLANNED,
        outcome=Outcome.SUCCESS,
        summary="Runtime upgrade is admissible under the base lock.",
        remediation="Review and commit the protected runtime lock diff.",
        details={
            "evaluator_core_version": plan.evaluator.core_version,
            "candidate_core_version": plan.candidate.core_version,
            "candidate_schema_version": plan.candidate.schema_version,
            "contracts": plan.contracts,
            "lock_diff": plan.lock_diff,
        },
    )


def _to_json_value(value: SupportedJsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: _to_json_value(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    return value


def result_to_dict(result: CommandResult) -> dict[str, JsonValue]:
    return {
        "schema_version": result.schema_version,
        "code": result.code.value,
        "outcome": result.outcome.value,
        "summary": result.summary,
        "remediation": result.remediation,
        "details": {
            key: _to_json_value(value) for key, value in result.details.items()
        },
    }


def render_json(result: CommandResult) -> str:
    return json.dumps(result_to_dict(result), allow_nan=False, sort_keys=True)


def _render_bootstrap_plan_detail(details: Mapping[str, object]) -> list[str]:
    """The findings and open questions of a bootstrap plan, for humans.

    Without this, `bootstrap plan` printed a one-line count and told the
    user to "answer the open questions" — while never saying what they
    were. The questions existed only in --json, and every form of --help
    errored, so the interview the command exists to drive was
    unreachable from the command itself.
    """
    lines: list[str] = []

    detected = details.get("detected")
    if isinstance(detected, Sequence) and not isinstance(detected, str):
        lines.append("")
        lines.append("Findings:")
        for finding in detected:
            if not isinstance(finding, Mapping):
                continue
            mark = "+" if finding.get("present") else "-"
            label = finding.get("label", finding.get("capability", "?"))
            lines.append(f"  {mark} {label}: {finding.get('detail', '')}")
            evidence = finding.get("evidence")
            if isinstance(evidence, Sequence) and not isinstance(evidence, str):
                for item in evidence:
                    lines.append(f"      {item}")

    actions = details.get("actions")
    if isinstance(actions, Sequence) and not isinstance(actions, str) and actions:
        lines.append("")
        lines.append("Proposed changes:")
        for action in actions:
            if isinstance(action, Mapping):
                # Show the action's own summary and rationale. An earlier
                # cut invented a `kind` key that does not exist and fell
                # back to a generic "change:" label, discarding the
                # justification the plan already carried — the user was
                # asked to approve writes with no stated reason.
                lines.append(f"  {action.get('summary', action.get('path', ''))}")
                rationale = action.get("rationale")
                if rationale:
                    lines.append(f"      {rationale}")
            else:
                lines.append(f"  {action}")

    questions = details.get("questions")
    if isinstance(questions, Sequence) and not isinstance(questions, str):
        # Answered questions are shown too, with the answer: a user
        # supplying them one at a time needs to see what is already
        # settled, not just what remains.
        open_questions = [
            q for q in questions
            if isinstance(q, Mapping) and q.get("answered") is None
        ]
        answered = [
            q for q in questions
            if isinstance(q, Mapping) and q.get("answered") is not None
        ]
        if answered:
            lines.append("")
            lines.append("Answered:")
            for question in answered:
                lines.append(f"  {question.get('id')} = {question.get('answered')}")
        if open_questions:
            lines.append("")
            lines.append(f"Open questions ({len(open_questions)}):")
            for question in open_questions:
                lines.append("")
                lines.append(f"  {question.get('id')}")
                lines.append(f"    {question.get('prompt', '')}")
                default = question.get("default")
                if default is not None:
                    lines.append(f"    default: {default}")

    return lines


# Human-readable detail bodies, keyed by result code. Keeping this in the
# presentation layer rather than adding a field to CommandResult means the
# JSON contract and result schema are untouched — the detail was always
# in `details`, it simply had no way to reach a human reader.
_DETAIL_RENDERERS: dict[ResultCode, Callable[[Mapping[str, object]], list[str]]] = {
    ResultCode.BOOTSTRAP_PLANNED: _render_bootstrap_plan_detail,
}


def render_human(result: CommandResult) -> str:
    # Help is the one result whose summary IS the message; prefixing it
    # with "success:" would frame documentation as a status report.
    if result.code is ResultCode.HELP_SHOWN:
        return f"{result.summary}\n\nNext: {result.remediation}"
    lines = [f"{result.outcome.value}: {result.summary}"]
    renderer = _DETAIL_RENDERERS.get(result.code)
    if renderer is not None:
        lines.extend(renderer(result.details))
    lines.append(f"Next: {result.remediation}")
    return "\n".join(lines)


# Help text for the Python-served commands, keyed by command path.
#
# These parsers are all built with add_help=False, deliberately: argparse's
# built-in help prints straight to stdout and raises SystemExit, which
# bypasses the CommandResult contract every other output here goes through
# (and so would never honour --json). The cost was that `--help` did not
# merely lack detail, it ERRORED — on `bootstrap`, `bootstrap plan`, and
# `-h` alike. For a command whose entire job is to interview the user,
# the one affordance a stuck user reaches for first returned
# "error: The command is invalid."
_HELP_TOPICS: dict[tuple[str, ...], str] = {
    (): (
        "agentharness — project bootstrap and runtime commands.\n"
        "\n"
        "  bootstrap plan    Inventory the project; report findings and\n"
        "                    the questions to answer. Read-only.\n"
        "  bootstrap apply   Apply a resolved, hash-confirmed plan.\n"
        "  status            Report the installed harness state.\n"
        "\n"
        "Run 'agentharness <command> --help' for detail. Setup commands\n"
        "(init, doctor, audit, update, uninstall) are served separately;\n"
        "run 'agentharness' with no arguments to list them."
    ),
    ("bootstrap",): (
        "agentharness bootstrap — first-run setup for a project.\n"
        "\n"
        "  plan     Inventory the project and report findings plus the\n"
        "           decisions to make. Writes nothing.\n"
        "  apply    Apply a fully answered plan, confirmed by hash.\n"
        "\n"
        "Typical flow:\n"
        "  agentharness bootstrap plan\n"
        "  agentharness bootstrap plan --answer rigor.tier=production ...\n"
        "  agentharness bootstrap apply --answer ... --confirm <plan-hash>"
    ),
    ("bootstrap", "plan"): (
        "agentharness bootstrap plan [DIR] — inventory a project. Read-only.\n"
        "\n"
        "  DIR                 Project to inspect (default: .); same as\n"
        "                      --target-dir below\n"
        "  --target-dir DIR    Project to inspect (default: .)\n"
        "  --answer KEY=VALUE  Answer one question; repeatable\n"
        "  --json              Machine-readable output\n"
        "\n"
        "Prints what was detected and every question still open, with\n"
        "its default. A plan is 'resolved' once no questions remain; only\n"
        "then can it be applied."
    ),
    ("bootstrap", "apply"): (
        "agentharness bootstrap apply [DIR] — apply a resolved plan.\n"
        "\n"
        "  DIR                 Project to modify (default: .); same as\n"
        "                      --target-dir below\n"
        "  --target-dir DIR    Project to modify (default: .)\n"
        "  --answer KEY=VALUE  Answer one question; repeatable\n"
        "  --confirm HASH      The plan hash being approved (required)\n"
        "  --json              Machine-readable output\n"
        "\n"
        "Refuses to run on an unresolved plan, without --confirm, or when\n"
        "the hash no longer matches — so it can never apply a plan other\n"
        "than the one that was reviewed."
    ),
}

_HELP_FLAGS = frozenset({"-h", "--help"})


def _help_result(argv: Sequence[str]) -> CommandResult | None:
    """A help result when *argv* asks for help, else None.

    Returned as a CommandResult rather than printed, so help obeys the
    same output contract as everything else.
    """
    if not any(arg in _HELP_FLAGS for arg in argv):
        return None
    path = tuple(arg for arg in argv if not arg.startswith("-"))
    # Fall back toward the most specific topic that exists, so
    # `bootstrap plan --json --help` and an unknown subcommand both land
    # somewhere useful instead of erroring.
    while path and path not in _HELP_TOPICS:
        path = path[:-1]
    return CommandResult(
        code=ResultCode.HELP_SHOWN,
        outcome=Outcome.SUCCESS,
        summary=_HELP_TOPICS[path],
        remediation=(
            "Run 'agentharness bootstrap plan' to inventory this project."
        ),
    )


def main(argv: Sequence[str] | None = None, output: TextIO | None = None) -> int:
    destination = output if output is not None else sys.stdout
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    help_result = _help_result(effective_argv)
    if help_result is not None:
        as_json = "--json" in effective_argv
        print(
            render_json(help_result) if as_json else render_human(help_result),
            file=destination,
        )
        return 0
    try:
        arguments = create_parser().parse_args(argv)
        if arguments.command == "status":
            result = execute_status()
        elif arguments.command == "bootstrap":
            # Prefer the positional target dir; fall back to --target-dir.
            # Same precedence as _dispatch_authority's repo_root/target_dir.
            target_dir = (
                arguments.target_dir_positional
                if arguments.target_dir_positional is not None
                else arguments.target_dir
            )
            if arguments.bootstrap_command == "plan":
                result = execute_bootstrap_plan(target_dir, arguments.answers)
            else:
                result = execute_bootstrap_apply(
                    target_dir, arguments.answers, arguments.confirm
                )
        elif arguments.command == "github":
            result = _dispatch_github(arguments)
        elif arguments.command == "profile":
            result = _dispatch_profile(arguments)
        elif arguments.command == "authority":
            result = _dispatch_authority(arguments)
        else:
            result = execute_runtime_plan_upgrade(
                arguments.request,
                arguments.base_lock,
            )
    except CommandUsageError:
        result = CommandResult(
            code=ResultCode.INVALID_COMMAND,
            outcome=Outcome.ERROR,
            summary="The command is invalid.",
            remediation="Run 'agentharness status' to inspect this project.",
        )
        print(render_human(result), file=destination)
        return 2

    as_json = getattr(arguments, "as_json", False)
    rendered = render_json(result) if as_json else render_human(result)
    print(rendered, file=destination)
    return 0 if result.outcome is Outcome.SUCCESS else 1


def _dispatch_github(arguments: argparse.Namespace) -> CommandResult:
    """Route github sub-commands."""
    if arguments.github_command == "protection":
        if arguments.prot_command == "plan":
            return execute_github_protection_plan(arguments.repo, arguments.branch)
        if arguments.prot_command == "apply":
            return execute_github_protection_apply(
                arguments.repo,
                arguments.branch,
                arguments.token_env,
            )
    if arguments.github_command == "completion":
        if arguments.comp_command == "check":
            return execute_github_completion_check(
                arguments.repo,
                arguments.pr,
                arguments.expected_head,
                arguments.token_env,
            )
    raise CommandUsageError

def _dispatch_profile(arguments: argparse.Namespace) -> CommandResult:
    """Route profile sub-commands (AC-10)."""
    if arguments.profile_command == "validate":
        return execute_profile_validate(arguments.file)
    if arguments.profile_command == "explain":
        return execute_profile_explain(arguments.file)
    if arguments.profile_command == "preview":
        return execute_profile_preview(arguments.file, arguments.current)
    if arguments.profile_command == "apply":
        return execute_profile_apply(arguments.file, arguments.target)
    raise CommandUsageError


def _dispatch_authority(arguments: argparse.Namespace) -> CommandResult:
    """Route authority sub-commands."""
    if arguments.authority_command == "check":
        # Prefer the check-local positional repo root; fall back to the
        # parent parser's --target-dir.
        target_dir = (
            arguments.repo_root
            if arguments.repo_root is not None
            else arguments.target_dir
        )
        return execute_authority_check(
            arguments.operation, arguments.target, target_dir
        )
    # Default: show authority info
    target_dir = arguments.target_dir
    as_json = arguments.as_json
    return execute_authority_info(as_json, target_dir)
