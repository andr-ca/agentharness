# Project Bootstrap Policy Slice 4 Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add language-independent quality modules for repository policy, configuration hygiene, documentation, changelog, composite commands, change classification, and safe generated integration.

**Architecture:** Bundled core plugins use the same plugin contract as the Python plugin. A canonical Git diff classifier binds committed classifications to exact ranges. Integration writers operate through declared create/managed-block/structured-merge/proposal strategies and update only canonical agent sources before invoking existing generators.

**Tech Stack:** Python, Git plumbing, JSON/YAML schemas, pytest fixtures, existing shell generators, markdownlint/link tooling, and GitHub workflow YAML.

---

## Task 1: Add repository, configuration, and composite-command plugins

**Files:**

- Create: `src/agentharness/plugins/core/__init__.py`
- Create: `src/agentharness/plugins/core/repository.py`
- Create: `src/agentharness/plugins/core/configuration.py`
- Create: `src/agentharness/plugins/core/composite.py`
- Create: `tests/fixtures/repository-policy/`
- Test: `tests/unit/plugins/core/test_repository.py`
- Test: `tests/unit/plugins/core/test_configuration.py`
- Test: `tests/unit/plugins/core/test_composite.py`

- [ ] **Step 1: Write failing fixtures**

Cover Git/trunk/hook settings, dirty/unborn repositories, `.env.sample`, secret-scanner tasks, canonical agent source/generators, `tools/check.sh`-style composite commands, includes, opaque commands, no-op weakening, and malformed task definitions.

- [ ] **Step 2: Observe failure**

Run: `python3 -m pytest tests/unit/plugins/core -q`

Expected: core plugins are absent.

- [ ] **Step 3: Implement conservative discovery/verification**

Record composite command material inputs and resolved effects; do not claim a composite covers tools that cannot be proven. Configuration hygiene recognizes existing systems and proposes `.env.sample` only when appropriate.

- [ ] **Step 4: Verify the bundled contract**

Run focused tests plus `tests/contract/test_bundled_plugins.py`.

Expected: every core plugin passes the same contract as the Python plugin.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/core tests/fixtures/repository-policy \
  tests/unit/plugins/core tests/contract/test_bundled_plugins.py
git commit -m "Discover repository and composite quality policy"
```

## Task 2: Implement canonical change ranges and hashes

**Files:**

- Create: `src/agentharness/policy/change_range.py`
- Create: `src/agentharness/policy/classification.py`
- Create: `src/agentharness/schemas/change-classification-v1.json`
- Test: `tests/unit/policy/test_change_range.py`
- Test: `tests/unit/policy/test_classification.py`
- Test: `tests/integration/test_classification_ranges.py`

- [ ] **Step 1: Write failing range/hash tests**

Cover commit index tree, push old/new and new branch, PR immutable SHAs, default push before/after, completion PR/upstream fallback, ambiguous base, add/delete/rename/copy/mode/symlink/submodule, odd filenames/NUL safety, and rebase invalidation.

- [ ] **Step 2: Observe failure**

Run the three focused test files.

Expected: change-range/classification modules are absent.

- [ ] **Step 3: Implement canonical tuple hashing**

Hash sorted NUL-delimited tuples of path, status, old/new mode, and old/new blob IDs. Exclude only `.agentharness-policy/changes/`; bind classifications separately to head and effective-policy hash. Reject a missing unique base with exact remediation.

- [ ] **Step 4: Verify every gate/range**

Run the integration matrix across temporary repositories.

Expected: expected hashes remain stable and any non-classification blob change invalidates.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/policy/change_range.py src/agentharness/policy/classification.py \
  src/agentharness/schemas/change-classification-v1.json tests/unit/policy \
  tests/integration/test_classification_ranges.py
git commit -m "Bind change classifications to canonical diffs"
```

## Task 3: Add documentation policy

**Files:**

- Create: `src/agentharness/plugins/core/documentation.py`
- Create: `tests/fixtures/documentation-policy/`
- Test: `tests/unit/plugins/core/test_documentation.py`
- Test: `tests/integration/test_documentation_policy.py`

- [ ] **Step 1: Write failing behavior tests**

Cover required entry points, public/API/architecture/operations path classes, internal links, snippets, generated drift, doc builds, refactor exclusion, explicit `no-documentation` reason/approver, missing/stale classification, and meaningless-edit resistance.

- [ ] **Step 2: Observe failure**

Run the two focused test files.

Expected: documentation plugin is absent.

- [ ] **Step 3: Implement change-aware verification**

Use committed classification and canonical ranges. A low-confidence change requests explicit classification; it never guesses public impact or requires arbitrary README churn.

- [ ] **Step 4: Verify fixtures**

Run focused tests.

Expected: public changes require an owned doc or protected disposition; internal-only changes do not.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/core/documentation.py tests/fixtures/documentation-policy \
  tests/unit/plugins/core/test_documentation.py tests/integration/test_documentation_policy.py
git commit -m "Enforce change-aware documentation policy"
```

## Task 4: Add changelog policy

**Files:**

- Create: `src/agentharness/plugins/core/changelog.py`
- Create: `tests/fixtures/changelog-policy/`
- Test: `tests/unit/plugins/core/test_changelog.py`
- Test: `tests/integration/test_changelog_policy.py`

- [ ] **Step 1: Write failing strategy tests**

Cover monolithic changelog, fragment workflow, valid fragment naming/content, existing release tool delegation, feature/fix/breaking classes, excluded internal/test changes, and protected `no-changelog` disposition.

- [ ] **Step 2: Observe failure**

Run the two focused test files.

Expected: changelog plugin is absent.

- [ ] **Step 3: Implement strategy-preserving verification**

Never convert an established monolithic/fragment system automatically. Generate proposals for absent strategies and bind enforcement to committed change classes.

- [ ] **Step 4: Verify fixtures**

Run focused tests.

Expected: applicable changes require exactly the configured strategy; excluded classes pass without churn.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/core/changelog.py tests/fixtures/changelog-policy \
  tests/unit/plugins/core/test_changelog.py tests/integration/test_changelog_policy.py
git commit -m "Enforce project changelog strategy"
```

## Task 5: Implement generated-file ownership and conflict strategies

**Files:**

- Create: `src/agentharness/integrations/__init__.py`
- Create: `src/agentharness/integrations/files.py`
- Create: `src/agentharness/integrations/managed_block.py`
- Create: `src/agentharness/integrations/structured_merge.py`
- Test: `tests/unit/integrations/test_files.py`
- Test: `tests/unit/integrations/test_managed_block.py`
- Test: `tests/unit/integrations/test_structured_merge.py`
- Test: `tests/integration/test_generated_conflicts.py`

- [ ] **Step 1: Write failing merge/path/TOCTOU tests**

Cover `create`, `managed-block`, `structured-merge`, `proposal-only`, unknown existing bytes, duplicate markers, malformed YAML/JSON/TOML, comments/unowned keys, symlinks, path escape, changed hash after plan, interrupted apply, and generated hash drift.

- [ ] **Step 2: Observe failure**

Run the focused unit/integration tests.

Expected: integration writers are absent.

- [ ] **Step 3: Implement ownership-safe writers**

Writers return planned bytes and metadata; the core transaction performs actual writes. Structured merges own explicit key paths and preserve unrelated content. Unknown conflicts pause with a reproducible patch.

- [ ] **Step 4: Verify round trips**

Run focused tests repeatedly and assert applying the same plan twice is a no-op.

Expected: idempotent output and no unrelated change.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/integrations tests/unit/integrations \
  tests/integration/test_generated_conflicts.py
git commit -m "Generate policy integrations without overwrites"
```

## Task 6: Generate hooks, workflows, CODEOWNERS, gitignore, and agent source

**Files:**

- Create: `src/agentharness/integrations/hooks.py`
- Create: `src/agentharness/integrations/github_workflow.py`
- Create: `src/agentharness/integrations/codeowners.py`
- Create: `src/agentharness/integrations/gitignore.py`
- Create: `src/agentharness/integrations/agents.py`
- Test: `tests/integration/test_generated_integrations.py`
- Test: `tests/integration/test_agent_generation.py`
- Modify: generator test fixtures as required

- [ ] **Step 1: Write failing integration-generation tests**

Cover existing hook dispatcher, workflow conflict, CODEOWNERS order/escaping/self-protection, gitignore markers, canonical agent source discovery, generator invocation, generated client drift, and no provable source/generator relationship.

- [ ] **Step 2: Observe failure**

Run the two focused integration files.

Expected: generators are absent.

- [ ] **Step 3: Implement deterministic proposals**

Protect profile, runtime, history, changes, schemas, plugins/providers, material inputs, canonical agent source, full workflow namespace, local Actions/status-producing scripts, integrations, and CODEOWNERS itself. Edit only the canonical agent source, then run recorded generators; otherwise emit proposal-only and leave bootstrap incomplete.

- [ ] **Step 4: Verify generated-client integrity**

Run focused tests plus all existing generator Bats suites.

Expected: source and generated clients agree; direct generated edits are detected.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/integrations tests/integration tools/tests
git commit -m "Generate protected policy integrations"
```

## Task 7: Add profile operations and explainability

**Files:**

- Create: `src/agentharness/profile/operations.py`
- Create: `src/agentharness/policy/explain.py`
- Modify: `src/agentharness/cli.py`
- Modify: `bin/cli.js`
- Test: `tests/integration/test_profile_commands.py`
- Test: `tests/integration/test_doctor_policy.py`
- Modify: `tests/integration/test_cli_routing.py`

- [ ] **Step 1: Write failing CLI operation tests**

Cover the exact public operations `profile show`, `profile explain
<requirement>`, `profile add <capability>`, `profile remove <capability>`,
`profile set <path> <value>`, `profile validate`, and `profile diff`. Assert
show/explain/validate/diff remain read-only and usable during incomplete
bootstrap; every mutating command previews by default and changes files only
with explicit `--apply`. Also cover additions, reductions, waivers, drift,
invalid schema, missing dependency, plugin mismatch, hook/CI/generated drift,
stale evidence, and illegal override.

- [ ] **Step 2: Observe failure**

Run the focused integration tests.

Expected: operations/explain implementations are absent.

- [ ] **Step 3: Implement stable operation/result codes**

Human output leads with outcome and next command; JSON output validates against
shipped schemas. `doctor --repair` produces and confirms a plan before any
write. Complete the public `profile show|explain|add|remove|set|validate|diff`,
`status`, `doctor`, and `audit` handlers in `cli.py`. Mutations accept `--apply`
after showing the deterministic plan; removal/weakening emits a protected
reduction proposal. Status separates discovery, active
requirements, deferred recommendations, and drift/evidence. The Node launcher
remains policy-free; install-state details come through Slice 1's typed legacy
adapter.

- [ ] **Step 4: Verify human and JSON snapshots**

Run focused tests plus `tests/integration/test_cli_routing.py`.

Expected: every failure includes precise remediation and no secret/path leak.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/profile/operations.py src/agentharness/policy/explain.py \
  src/agentharness/cli.py bin/cli.js tests/integration/test_profile_commands.py \
  tests/integration/test_doctor_policy.py tests/integration/test_cli_routing.py
git commit -m "Explain and repair committed policy state"
```

## Task 8: Verify Slice 4 and update evidence

**Files:**

- Modify: `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run slice verification**

```bash
python3 -m pytest tests/unit/plugins/core tests/unit/integrations \
  tests/unit/policy/test_change_range.py tests/unit/policy/test_classification.py \
  tests/integration/test_classification_ranges.py \
  tests/integration/test_documentation_policy.py \
  tests/integration/test_changelog_policy.py \
  tests/integration/test_generated_conflicts.py \
  tests/integration/test_generated_integrations.py \
  tests/integration/test_agent_generation.py -q
bats tools/tests/generate-*.bats
ruff check src/agentharness tests
mypy src/agentharness
bash tools/check.sh
```

Expected: all pass.

- [ ] **Step 2: Update implemented rows**

Update AC-04's core portion, AC-10, AC-15, AC-18, AC-27, and the local generated portions of AC-20, AC-24, and AC-31 where actually evidenced.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md CHANGELOG.md
git commit -m "Record core quality implementation evidence"
```
