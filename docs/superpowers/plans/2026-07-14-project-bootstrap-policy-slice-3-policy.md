# Project Bootstrap Policy Slice 3 Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile one committed profile into deterministic commit, push, CI, and completion gate plans with fresh, structured, non-forgeable evidence.

**Architecture:** A pure compiler resolves typed requirements into gate-specific verification requests and effective-policy hashes. A verifier executes argument arrays, aggregates typed results, stores local/CI evidence, and rejects stale fingerprints. Gate adapters provide canonical Git/tree/range context but never duplicate policy.

**Tech Stack:** Python, Git plumbing commands, pytest/Hypothesis, Bats hook fixtures, JSON evidence artifacts, and GitHub Actions templates.

---

## Task 1: Compile requirements and scope expressions

**Files:**

- Create: `src/agentharness/policy/__init__.py`
- Create: `src/agentharness/policy/scope.py`
- Create: `src/agentharness/policy/compiler.py`
- Create: `src/agentharness/policy/results.py`
- Test: `tests/unit/policy/test_scope.py`
- Test: `tests/unit/policy/test_compiler.py`

- [ ] **Step 1: Write failing compiler/property tests**

Cover stable ordering, duplicate IDs, invalid providers, four gates, include/exclude path expressions, change classes, modes, dependencies, cycles, unavailable capabilities, expensive-gate placement, and equivalent-profile hashing.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/policy/test_scope.py tests/unit/policy/test_compiler.py -q`

Expected: policy modules are missing.

- [ ] **Step 3: Implement the pure compiler**

Return immutable `EffectivePolicy` and `GatePlan` records. Hash canonical JSON containing normalized profile, runtime, plugin/provider identities, compiler version, and material inputs. `warn` and `grace` affect aggregation, not whether requirements disappear from plans.

- [ ] **Step 4: Verify determinism**

Run focused tests with Hypothesis statistics and two randomized process hash seeds.

Expected: byte-identical plans and hashes.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/policy tests/unit/policy
git commit -m "Compile one profile into deterministic gate plans"
```

## Task 2: Fingerprint every material input

**Files:**

- Create: `src/agentharness/policy/fingerprint.py`
- Create: `src/agentharness/policy/git_tree.py`
- Test: `tests/unit/policy/test_fingerprint.py`
- Test: `tests/integration/test_evidence_inputs.py`

- [ ] **Step 1: Write a failing parameterized invalidation matrix**

Change code, staged tree, base/head, classification, profile, runtime, plugin, tool version, task definition, included script, tool config, dependency lock, environment allowlist, and compiler version one at a time. Assert each changes the fingerprint; irrelevant untracked/cache files do not.

- [ ] **Step 2: Observe the failure**

Run the two focused test files.

Expected: fingerprint implementation is absent.

- [ ] **Step 3: Implement canonical fingerprints**

Use Git object IDs and NUL-delimited length-safe encodings. Commit fingerprints use a temporary tree made from the index, never working-tree bytes. Record missing/opaque material inputs as errors in strict mode.

- [ ] **Step 4: Verify all invalidation classes**

Run: `python3 -m pytest tests/unit/policy/test_fingerprint.py tests/integration/test_evidence_inputs.py -q`

Expected: every specified relevant mutation invalidates; irrelevant mutations remain stable.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/policy/fingerprint.py src/agentharness/policy/git_tree.py \
  tests/unit/policy/test_fingerprint.py tests/integration/test_evidence_inputs.py
git commit -m "Bind policy evidence to material inputs"
```

## Task 3: Execute checks and persist redacted evidence

**Files:**

- Create: `src/agentharness/policy/verifier.py`
- Create: `src/agentharness/policy/evidence.py`
- Create: `src/agentharness/policy/redaction.py`
- Modify: `src/agentharness/cli.py`
- Create: `src/agentharness/schemas/evidence-v1.json`
- Test: `tests/unit/policy/test_verifier.py`
- Test: `tests/unit/policy/test_evidence.py`
- Test: `tests/unit/policy/test_redaction.py`
- Test: `tests/integration/test_verify_command.py`
- Test: `tests/integration/test_fail_closed.py`

- [ ] **Step 1: Write failing execution/error/redaction tests**

Cover argument arrays, timeout, signal, missing executable, malformed plugin
result, pass/fail/warn/not-applicable/error, strict aggregation, output caps,
token/password/URI/user-home redaction, atomic evidence writes, stale evidence
rejection, and public `verify --gate commit|push|ci|completion [--json]` routing.

- [ ] **Step 2: Observe the failure**

Run the three focused unit files plus `tests/integration/test_verify_command.py`
and `tests/integration/test_fail_closed.py`.

Expected: verifier/evidence modules are missing.

- [ ] **Step 3: Implement execution and evidence schema**

Never use `shell=True` for ordinary requirements. Stream bounded output through
redaction, preserve a diagnostic hash, and write local evidence under
`.agentharness-local/evidence/<policy-hash>/<gate>/`. CI emits the identical
schema to a caller-selected artifact directory. Wire `verify` through
`cli.py`; unsupported future completion context returns an honest typed error
until Slice 5 supplies it.

- [ ] **Step 4: Verify branch coverage**

Run: `python3 -m pytest tests/unit/policy/test_verifier.py tests/unit/policy/test_evidence.py tests/unit/policy/test_redaction.py tests/integration/test_verify_command.py tests/integration/test_fail_closed.py --cov=agentharness.policy --cov-branch --cov-fail-under=80 -q`

Expected: pass with no secret fixture content in captured output/files.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/policy/verifier.py src/agentharness/policy/evidence.py \
  src/agentharness/policy/redaction.py src/agentharness/schemas/evidence-v1.json \
  src/agentharness/cli.py tests/unit/policy tests/integration/test_verify_command.py \
  tests/integration/test_fail_closed.py
git commit -m "Emit fresh redacted policy evidence"
```

## Task 4: Implement deterministic strict, warn, grace, and waivers

**Files:**

- Create: `src/agentharness/policy/modes.py`
- Create: `src/agentharness/profile/waivers.py`
- Test: `tests/unit/policy/test_modes.py`
- Test: `tests/unit/profile/test_waivers.py`

- [ ] **Step 1: Write failing time/commit-budget tests**

Use an injected clock and Git graph fixtures. Cover grace anchor SHA, UTC deadline, max commit count, rewrites/missing anchor, expiry boundary, malformed/broad waiver, scope mismatch, missing reason/owner/approver, and no general skip flag.

- [ ] **Step 2: Observe the failure**

Run the focused tests.

Expected: modes/waivers modules are missing.

- [ ] **Step 3: Implement committed-field evaluation**

Count commits with `git rev-list --count <anchor>..<head>` after verifying ancestry. A waiver changes one explicit requirement/scope result and remains visible in evidence; it never mutates the compiled policy or authorizes publication.

- [ ] **Step 4: Verify boundary cases**

Run focused tests with timezone varied across at least UTC, Toronto, and Tokyo.

Expected: identical UTC decisions.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/policy/modes.py src/agentharness/profile/waivers.py \
  tests/unit/policy/test_modes.py tests/unit/profile/test_waivers.py
git commit -m "Enforce deterministic policy modes and waivers"
```

## Task 5: Implement commit and push gate contexts

**Files:**

- Create: `src/agentharness/gates/__init__.py`
- Create: `src/agentharness/gates/commit.py`
- Create: `src/agentharness/gates/push.py`
- Create: `src/agentharness/gates/context.py`
- Test: `tests/integration/test_commit_gate.py`
- Test: `tests/integration/test_push_gate.py`

- [ ] **Step 1: Write failing disposable-repository tests**

Cover partially staged files, unstaged dependencies, rename/mode/symlink changes, unborn branch, new branch, force push, deletion, multiple refs, remote old/new SHA input, detached HEAD, and missing authoritative base.

- [ ] **Step 2: Observe the failure**

Run the two integration files.

Expected: gate modules are missing.

- [ ] **Step 3: Implement context construction**

The commit gate reads the index via Git plumbing and reports misleading unstaged dependencies. The push gate consumes stdin ref updates exactly as Git supplies them, verifies remote/object availability, and computes a merge-base fallback only for new branches.

- [ ] **Step 4: Verify real hook invocation**

Run the integration tests against temporary bare remotes.

Expected: required failures block commit/push with stable remediation; passing changes proceed.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/gates tests/integration/test_commit_gate.py \
  tests/integration/test_push_gate.py
git commit -m "Verify staged trees and outgoing revisions"
```

## Task 6: Implement CI and base-trusted policy integrity

**Files:**

- Create: `src/agentharness/gates/ci.py`
- Create: `src/agentharness/policy/integrity.py`
- Modify: `src/agentharness/runtime_lock.py`
- Modify: `templates/bootstrap/verify-runtime.mjs`
- Create: `src/agentharness/schemas/ci-context-v1.json`
- Test: `tests/integration/test_ci_gate.py`
- Test: `tests/integration/test_base_trust.py`
- Test: `tests/integration/test_workflow_identity.py`

- [ ] **Step 1: Write failing event and spoof tests**

Cover PR immutable base/head, default-branch before/after, missing event fields,
base retrieval of bootstrapper and complete consumer lock, separate npm/runtime
download and digest checks, zipapp internal identity checks, base-runtime
authority during upgrade PRs, untrusted head bootstrapper/lock changes,
duplicate job names in any workflow, reusable workflows, local Actions,
scripts/configs producing required results, and unsupported identity boundaries.

- [ ] **Step 2: Observe the failure**

Run the three integration files.

Expected: CI/integrity modules are missing.

- [ ] **Step 3: Implement authoritative CI context and namespace scan**

The bootstrapper and complete runtime lock come from the base commit for PRs.
The bootstrapper verifies and extracts the exact npm tarball and selected Python
runtime separately, confirms zipapp/core/schema/plugin/provider identities, and
only then executes the gate. Upgrade PRs remain evaluated by the base runtime
while the candidate runs only the isolated contract defined in Slice 1. Parse
all workflow YAML without executing head code. Stable required contexts include
repository-unique overall-policy and policy-integrity names; collisions or
unprotected producers fail strict activation.

- [ ] **Step 4: Verify adversarial suite**

Run focused integration tests.

Expected: every spoof attempt fails even when it emits a nominal success context.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/gates/ci.py src/agentharness/policy/integrity.py \
  src/agentharness/runtime_lock.py templates/bootstrap/verify-runtime.mjs \
  src/agentharness/schemas/ci-context-v1.json tests/integration/test_ci_gate.py \
  tests/integration/test_base_trust.py tests/integration/test_workflow_identity.py
git commit -m "Protect authoritative CI policy identity"
```

## Task 7: Add thin local hook and CI dispatchers

**Files:**

- Create: `templates/hooks/pre-commit`
- Create: `templates/hooks/pre-push`
- Create: `templates/github/agentharness-policy.yml`
- Create: `src/agentharness/integrations/hashes.py`
- Test: `.github/hooks/tests/policy-dispatch.bats`
- Test: `tests/integration/test_gate_compilation.py`

- [ ] **Step 1: Write failing dispatcher tests**

Assert generated files contain only runtime/bootstrap invocation, gate, event/ref context, and generator hash; no requirement IDs, thresholds, exclusions, or duplicated policy values.

- [ ] **Step 2: Observe the failure**

Run: `bats .github/hooks/tests/policy-dispatch.bats && python3 -m pytest tests/integration/test_gate_compilation.py -q`

Expected: templates/generator hashes are absent.

- [ ] **Step 3: Implement minimal templates**

Preserve incoming pre-push stdin. Use base-trusted bootstrap in CI. Include least-privilege permissions and artifact upload for evidence. Completion remains a local/remote adapter added in Slice 5.

- [ ] **Step 4: Verify four-plan coherence**

Run focused tests and inspect generated fixtures.

Expected: commit, push, CI, and placeholder completion plans carry one effective-policy hash.

- [ ] **Step 5: Commit**

```bash
git add templates/hooks templates/github src/agentharness/integrations/hashes.py \
  .github/hooks/tests/policy-dispatch.bats tests/integration/test_gate_compilation.py
git commit -m "Generate thin policy gate dispatchers"
```

## Task 8: Verify Slice 3 and update evidence

**Files:**

- Modify: `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run slice verification**

```bash
python3 -m pytest tests/unit/policy tests/unit/profile/test_waivers.py \
  tests/integration/test_commit_gate.py tests/integration/test_push_gate.py \
  tests/integration/test_ci_gate.py tests/integration/test_base_trust.py \
  tests/integration/test_workflow_identity.py tests/integration/test_gate_compilation.py \
  tests/integration/test_verify_command.py tests/integration/test_fail_closed.py \
  --cov=agentharness.policy --cov=agentharness.gates --cov-branch --cov-fail-under=80
bats .github/hooks/tests/policy-dispatch.bats
ruff check src/agentharness/policy src/agentharness/gates tests
mypy src/agentharness/policy src/agentharness/gates
bash tools/check.sh
```

Expected: all pass.

- [ ] **Step 2: Update implemented rows**

Update AC-08, AC-11 through AC-15, AC-17, AC-21's local portion, AC-25's policy portion, and AC-31's local-integrity portion only where evidence exists.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md CHANGELOG.md
git commit -m "Record deterministic gate implementation evidence"
```
