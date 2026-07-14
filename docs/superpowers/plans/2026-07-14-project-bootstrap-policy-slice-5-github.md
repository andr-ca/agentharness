# Project Bootstrap Policy Slice 5 GitHub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply and prove GitHub enforcement, gate agent completion on exact-head CI and review state, and safely remove active policy through a protected three-PR transaction.

**Architecture:** A typed GitHub adapter separates read, plan, apply, and read-back. Remote mutations are resumable and limited to confirmed diffs. Completion correlates exact-head checks, reviews, threads, and marked acknowledgements. Decommission is an explicit state machine retaining a proven temporary producer until no remote rule references it.

**Tech Stack:** Python standard-library HTTP, GitHub REST and GraphQL APIs, pytest fake server, recorded sanitized fixtures, GitHub Actions, and an explicitly authorized sandbox repository.

---

## Task 1: Implement the typed GitHub API boundary

**Files:**

- Create: `src/agentharness/remote/__init__.py`
- Create: `src/agentharness/remote/github/__init__.py`
- Create: `src/agentharness/remote/github/api.py`
- Create: `src/agentharness/remote/github/models.py`
- Create: `src/agentharness/remote/github/auth.py`
- Create: `tests/fakes/github_server.py`
- Test: `tests/unit/remote/github/test_api.py`
- Test: `tests/unit/remote/github/test_auth.py`

- [ ] **Step 1: Write failing HTTP/auth/error tests**

Cover REST/GraphQL pagination, rate limits, retryable/non-retryable responses, timeout, ambiguous write result, malformed JSON, missing fields, token redaction, unauthenticated `gh`, repository/host identity, and least-privilege permission diagnostics.

- [ ] **Step 2: Observe failure**

Run: `python3 -m pytest tests/unit/remote/github -q`

Expected: remote modules are absent.

- [ ] **Step 3: Implement the boundary**

Use `urllib.request` with injected transport/clock/sleeper. Retries apply only to idempotent reads or writes with a safe reconciliation key. Never log authorization headers, query variables containing sensitive values, or full environment data.

- [ ] **Step 4: Verify fake-server behavior**

Run focused tests.

Expected: stable typed failures and no token string in output/captured requests.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/remote tests/fakes tests/unit/remote
git commit -m "Add typed GitHub policy API boundary"
```

## Task 2: Read, plan, apply, and verify protection minimally

**Files:**

- Create: `src/agentharness/remote/github/protection.py`
- Create: `src/agentharness/remote/github/rulesets.py`
- Modify: `src/agentharness/cli.py`
- Create: `src/agentharness/schemas/protection-plan-v1.json`
- Test: `tests/unit/remote/github/test_protection.py`
- Test: `tests/integration/test_github_reconcile.py`
- Test: `tests/integration/test_protection_commands.py`

- [ ] **Step 1: Write failing plan/reconcile tests**

Cover branch protection, rulesets, required workflows when available, required contexts, App source, total approvals, code-owner review, stale approval dismissal, conversation resolution, direct-push restrictions, unrelated existing settings, permissions failure, unsupported host/plan, partial writes, and read-back mismatch.

- [ ] **Step 2: Observe failure**

Run the focused unit/integration files.

Expected: protection adapters are absent.

- [ ] **Step 3: Implement minimal confirmed diffs**

Read first, compute a field-level plan, require repository/default-branch
confirmation, apply only owned fields, then read back and compare semantic
state. Prefer required workflows pinned to protected source when the
organization supports them; otherwise require enforceable ownership of every
status-producing input. Strict mode stays incomplete if neither boundary
exists. Wire `protection plan|apply|verify` through `cli.py` and require an
explicit confirmed plan hash for apply.

- [ ] **Step 4: Verify fault injection and preservation**

Run reconciliation tests with failure after every write.

Expected: resume reads actual state and converges without erasing unrelated settings.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/remote/github/protection.py \
  src/agentharness/remote/github/rulesets.py \
  src/agentharness/schemas/protection-plan-v1.json \
  src/agentharness/cli.py tests/unit/remote/github/test_protection.py \
  tests/integration/test_github_reconcile.py tests/integration/test_protection_commands.py
git commit -m "Apply GitHub protection with verified read-back"
```

## Task 3: Model reductions, CODEOWNERS, approvals, and waivers precisely

**Files:**

- Create: `src/agentharness/remote/github/ownership.py`
- Create: `src/agentharness/remote/github/approvals.py`
- Test: `tests/unit/remote/github/test_ownership.py`
- Test: `tests/unit/remote/github/test_approvals.py`
- Test: `tests/integration/test_reduction_approval.py`

- [ ] **Step 1: Write failing semantic tests**

Cover base-branch CODEOWNERS location/order/escaping, owner access validation, one matching owner approval, separately configured total approval count, stale/dismissed/changes-requested reviews, CODEOWNERS self-protection, isolated reduction path allowlist, mixed product changes, and protected waivers.

- [ ] **Step 2: Observe failure**

Run focused tests.

Expected: ownership/approval modules are absent.

- [ ] **Step 3: Implement exact GitHub semantics**

Do not claim multiple approvals from a specific owner set. A reduction exception permits only registered policy/material/generated surfaces and cannot satisfy completion until required review passes. Report the exact missing owner/total-review condition.

- [ ] **Step 4: Verify false-approval cases**

Run focused tests.

Expected: team membership/access and approval state are read from current base/head context; stale approvals never count.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/remote/github/ownership.py \
  src/agentharness/remote/github/approvals.py tests/unit/remote/github \
  tests/integration/test_reduction_approval.py
git commit -m "Enforce protected policy reduction approvals"
```

## Task 4: Fetch review signals, comments, and thread state

**Files:**

- Create: `src/agentharness/remote/github/reviews.py`
- Create: `src/agentharness/remote/github/acknowledgements.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/remote/github/test_reviews.py`
- Test: `tests/unit/remote/github/test_acknowledgements.py`
- Test: `tests/integration/test_review_lifecycle.py`
- Test: `tests/integration/test_review_commands.py`

- [ ] **Step 1: Write failing review/comment matrix**

Cover expected check/reviewer/App signals, allowed terminal states, timeout, stabilization interval, new activity after first fetch, issue comments, inline comments, GraphQL thread resolution, direct replies, hidden marker parsing, stale claimed action, bot authors, self/status/superseded exclusions, pagination, edits, and deleted comments.

- [ ] **Step 2: Observe failure**

Run the focused tests.

Expected: review modules are absent.

- [ ] **Step 3: Implement marker-correlated acknowledgement**

Use a versioned hidden marker containing source type/ID and assessment hash.
Post issue-level replies through PR comments and inline replies through the
review-comment reply endpoint. Re-fetch after stabilization and reject
acknowledgements whose claimed commit/action does not apply to current head.
Wire `review acknowledge` through `cli.py`; require source comment identity,
assessment, and action/commit fields and show the exact generated reply before
posting.

- [ ] **Step 4: Verify no recursive acknowledgement**

Run focused tests.

Expected: generated acknowledgements/status messages are excluded by typed rules while human/bot findings remain in scope.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/remote/github/reviews.py \
  src/agentharness/remote/github/acknowledgements.py \
  src/agentharness/cli.py tests/unit/remote/github \
  tests/integration/test_review_lifecycle.py tests/integration/test_review_commands.py
git commit -m "Correlate GitHub review acknowledgements"
```

## Task 5: Implement exact-head completion gating

**Files:**

- Create: `src/agentharness/gates/completion.py`
- Create: `src/agentharness/remote/github/completion.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/remote/github/test_completion.py`
- Test: `tests/integration/test_completion_gate.py`
- Test: `tests/integration/test_publish_authority.py`

- [ ] **Step 1: Write failing completion table**

Cover dirty index/worktree, uncommitted request, unauthorized publication, unpublished commit, stale/missing/red CI, exact SHA mismatch, pending expected review, changes requested, insufficient approvals, unresolved thread, unacknowledged issue/inline comment, stale evidence, and reusable exact-commit CI evidence.

- [ ] **Step 2: Observe failure**

Run focused tests.

Expected: completion modules are absent.

- [ ] **Step 3: Implement ordered completion evaluation**

Evaluate local state, authority/publication, exact-head CI, expected
signals/stabilization, reviews/threads/comments, then evidence freshness. Wire
the completed remote context into `verify --gate completion`. The gate may
report `verified locally; publication awaiting authorization`; it never creates
authority or calls push/PR/merge by itself.

- [ ] **Step 4: Verify all blockers and success path**

Run focused tests.

Expected: each blocker has a stable code and exact remediation; success binds current head SHA and effective-policy hash.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/gates/completion.py \
  src/agentharness/remote/github/completion.py src/agentharness/cli.py \
  tests/unit/remote/github/test_completion.py \
  tests/integration/test_completion_gate.py tests/integration/test_publish_authority.py
git commit -m "Gate completion on exact GitHub state"
```

## Task 6: Implement protected three-PR decommission

**Files:**

- Create: `src/agentharness/remote/github/decommission.py`
- Modify: `src/agentharness/cli.py`
- Create: `templates/github/agentharness-decommission.yml`
- Create: `src/agentharness/schemas/decommission-state-v1.json`
- Test: `tests/unit/remote/github/test_decommission.py`
- Test: `tests/integration/test_decommission.py`

- [ ] **Step 1: Write failing state/fault/rollback tests**

Cover intent, temporary producer install, PR/default-branch success/read-back, context replacement, PR 2 allowed diff, removal/read-back, PR 3 cleanup, rollback before PR 2, restart/resume at every state, unexpected head/default branch, unrelated changes, and orphan required contexts.

- [ ] **Step 2: Observe failure**

Run focused tests.

Expected: decommission module/template are absent.

- [ ] **Step 3: Implement explicit resumable states**

Persist intent and remote snapshots without tokens. Never require the temporary
context before proving its exact job/App/runtime/intent on both PR and resulting
default branch. Never delete its producer before read-back proves no rule
references it. Wire `decommission plan|--resume` and active-policy `uninstall`
redirection through `cli.py`.

- [ ] **Step 4: Verify state-transition coverage**

Run: `python3 -m pytest tests/unit/remote/github/test_decommission.py tests/integration/test_decommission.py --cov=agentharness.remote.github.decommission --cov-branch --cov-fail-under=80 -q`

Expected: state transitions meet the repository's Production-tier branch-coverage floor.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/remote/github/decommission.py \
  templates/github/agentharness-decommission.yml \
  src/agentharness/schemas/decommission-state-v1.json \
  src/agentharness/cli.py \
  tests/unit/remote/github/test_decommission.py tests/integration/test_decommission.py
git commit -m "Decommission policy through protected transaction"
```

## Task 7: Prove behavior in an authorized GitHub sandbox

**Files:**

- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_activation.py`
- Create: `tests/e2e/test_reductions.py`
- Create: `tests/e2e/test_completion.py`
- Create: `tests/e2e/test_decommission.py`
- Create: `tests/e2e/README.md`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add opt-in E2E tests with safety guards**

Require `AGENTHARNESS_GITHUB_E2E=1`, an allowlisted repository full name, non-production marker topic/file, admin-capable token, clean initial snapshot, and explicit teardown/reconciliation. Default CI must collect but skip these tests with a clear reason.

- [ ] **Step 2: Run against fake transport first**

Run: `python3 -m pytest tests/e2e --collect-only -q && python3 -m pytest tests/integration/test_github_reconcile.py tests/integration/test_review_lifecycle.py tests/integration/test_decommission.py -q`

Expected: collection and fake integration pass.

- [ ] **Step 3: Run the authorized sandbox sequence**

Run: `AGENTHARNESS_GITHUB_E2E=1 AGENTHARNESS_E2E_REPO=<owner/sandbox> python3 -m pytest tests/e2e -m github_sandbox -v`

Expected: activation, protected reduction, review completion, and decommission all pass; final remote snapshot has no orphan context.

- [ ] **Step 4: Archive sanitized evidence**

Store exact repository, PR/run IDs, head SHAs, semantic before/after protection snapshots, and teardown result as CI artifacts. Do not store tokens or raw headers.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e .github/workflows/ci.yml
git commit -m "Verify policy protection in GitHub sandbox"
```

## Task 8: Verify Slice 5 and update evidence

**Files:**

- Modify: `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run local and sandbox gates**

```bash
python3 -m pytest tests/unit/remote tests/integration/test_github_reconcile.py \
  tests/integration/test_protection_commands.py \
  tests/integration/test_reduction_approval.py tests/integration/test_review_lifecycle.py \
  tests/integration/test_review_commands.py \
  tests/integration/test_completion_gate.py tests/integration/test_publish_authority.py \
  tests/integration/test_decommission.py -q
AGENTHARNESS_GITHUB_E2E=1 AGENTHARNESS_E2E_REPO=<owner/sandbox> \
  python3 -m pytest tests/e2e -m github_sandbox -v
ruff check src/agentharness/remote src/agentharness/gates tests
mypy src/agentharness/remote src/agentharness/gates
bash tools/check.sh
```

Expected: local and authorized remote tests pass.

- [ ] **Step 2: Update verified rows**

Use actual sandbox evidence to update AC-03's remote portion and AC-20 through AC-26 and AC-31. Do not mark any remote outcome verified from mocks alone.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md CHANGELOG.md
git commit -m "Record GitHub policy enforcement evidence"
```
