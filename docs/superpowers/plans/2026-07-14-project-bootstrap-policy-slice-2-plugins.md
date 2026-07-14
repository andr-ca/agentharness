# Project Bootstrap Policy Slice 2 Plugins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a versioned plugin SDK, compliance suite, and complete Python plugin that discovers every approved capability without weakening existing project checks.

**Architecture:** Plugins are trusted, version-pinned data providers invoked by a core-owned runner. Discovery and planning are side-effect free; typed findings carry evidence, confidence, provenance, material inputs, and remediation. Capability-specific detector modules remain independent and combine through one Python plugin.

**Tech Stack:** Python protocols/dataclasses, pytest contract tests, fixture repositories, TOML via `tomllib`, safe YAML through the core loader, and subprocess argument arrays.

---

## Task 1: Define the plugin contract and registry

**Files:**

- Create: `src/agentharness/plugins/__init__.py`
- Create: `src/agentharness/plugins/api.py`
- Create: `src/agentharness/plugins/registry.py`
- Create: `src/agentharness/plugins/runner.py`
- Create: `src/agentharness/plugins/trust.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/plugins/test_registry.py`
- Test: `tests/unit/plugins/test_runner.py`
- Test: `tests/unit/plugins/test_trust.py`
- Test: `tests/integration/test_plugin_commands.py`

- [ ] **Step 1: Write failing contract-boundary tests**

Cover stable metadata IDs, compatible core/schema ranges, declared permissions, duplicate capability ownership, deterministic ordering, timeout/error conversion, output redaction, no arbitrary consumer imports, and exact third-party trust/version requirements.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/plugins -q`

Expected: plugin API modules are missing.

- [ ] **Step 3: Implement typed contract and runner**

Define `PluginMetadata`, `Finding`, `Question`, `Recommendation`, `ChangePlan`,
`CheckResult`, `Remediation`, and context/request records. The runner validates
all returned objects and converts plugin exceptions into typed errors without
exposing secrets. Wire `plugins list|inspect|trust|remove` through `cli.py`;
third-party trust/removal produces a protected profile plan rather than a local
mutable registry edit.

- [ ] **Step 4: Verify focused suite**

Run: `python3 -m pytest tests/unit/plugins tests/integration/test_plugin_commands.py -q --cov=agentharness.plugins --cov-branch --cov-fail-under=80`

Expected: pass at the repository's Production-tier branch-coverage floor.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins src/agentharness/cli.py tests/unit/plugins \
  tests/integration/test_plugin_commands.py
git commit -m "Define versioned bootstrap plugin contract"
```

## Task 2: Build the shared plugin compliance suite and sample plugin

**Files:**

- Create: `tests/contract/conftest.py`
- Create: `tests/contract/plugin_compliance.py`
- Create: `tests/contract/test_bundled_plugins.py`
- Create: `tests/contract/test_capability_coverage.py`
- Create: `examples/plugins/sample-quality/README.md`
- Create: `examples/plugins/sample-quality/plugin.py`
- Create: `examples/plugins/sample-quality/test_contract.py`

- [ ] **Step 1: Write the failing compliance suite against deliberately broken plugins**

Include fixtures for nondeterminism, mutation during discovery, undeclared command execution, malformed schema, unredacted secret, unstable IDs, path escape, unsupported result code, and vague remediation.

- [ ] **Step 2: Observe failures by category**

Run: `python3 -m pytest tests/contract -q`

Expected: each broken fixture fails with its intended contract code.

- [ ] **Step 3: Implement reusable compliance assertions and sample plugin**

The sample must demonstrate every public method with minimal behavior and pass without private test helpers. Document plugin trust and version pinning; do not present the sample as production language support.

- [ ] **Step 4: Verify the public sample**

Run: `python3 -m pytest tests/contract examples/plugins/sample-quality/test_contract.py -q`

Expected: bundled placeholder list and sample pass; broken fixtures remain expected failures inside meta-tests.

- [ ] **Step 5: Commit**

```bash
git add tests/contract examples/plugins/sample-quality
git commit -m "Test bootstrap plugins against shared contract"
```

## Task 3: Detect Python environment and task indirection

**Files:**

- Create: `src/agentharness/plugins/python/__init__.py`
- Create: `src/agentharness/plugins/python/plugin.py`
- Create: `src/agentharness/plugins/python/environment.py`
- Create: `src/agentharness/plugins/python/tasks.py`
- Create: `src/agentharness/plugins/python/material_inputs.py`
- Create: `tests/fixtures/python/environment/`
- Create: `tests/fixtures/python/tasks/`
- Test: `tests/unit/plugins/python/test_environment.py`
- Test: `tests/unit/plugins/python/test_tasks.py`

- [ ] **Step 1: Add failing fixture-driven tests**

Cover `pyproject.toml`, setup files, requirements, uv, Poetry, Pipenv, tox, nox, Make, conflicting entry points, includes, dependency locks, opaque shell tasks, malformed configuration, and symlink/path escapes.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/plugins/python/test_environment.py tests/unit/plugins/python/test_tasks.py -q`

Expected: Python plugin modules are missing.

- [ ] **Step 3: Implement evidence-backed environment/task resolution**

Prefer declared public tasks over guessed raw commands. Record every material task/configuration/dependency input and the resolved underlying tool/effect when provable. Mark opaque tasks honestly; never infer success from a target name.

- [ ] **Step 4: Verify fixtures and determinism**

Run the focused tests twice with randomized fixture enumeration and compare serialized findings byte-for-byte.

Expected: identical results and no project mutation.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/python tests/fixtures/python/environment \
  tests/fixtures/python/tasks tests/unit/plugins/python
git commit -m "Discover Python environments and material tasks"
```

## Task 4: Detect Python lint, formatting, typing, and unit testing

**Files:**

- Create: `src/agentharness/plugins/python/linting.py`
- Create: `src/agentharness/plugins/python/typing.py`
- Create: `src/agentharness/plugins/python/testing.py`
- Create: `tests/fixtures/python/quality/`
- Test: `tests/unit/plugins/python/test_linting.py`
- Test: `tests/unit/plugins/python/test_typing.py`
- Test: `tests/unit/plugins/python/test_testing.py`

- [ ] **Step 1: Add failing matrix cases**

Cover Ruff, Black, Flake8, Pylint, isort, mypy, Pyright, pytest, unittest, coverage, CI-only commands, multiple tools, dependency-without-config, config-without-runnable-command, and conflicting thresholds.

- [ ] **Step 2: Observe the failure**

Run the three focused test files.

Expected: missing detector implementations.

- [ ] **Step 3: Implement presence/configured/runnable/enforced states**

Bind only high-confidence runnable checks. Record actual arguments, scope, threshold, public task, tool version source, and material inputs. Recommendations propose the smallest coherent baseline only when no established check exists.

- [ ] **Step 4: Verify expected findings**

Run: `python3 -m pytest tests/unit/plugins/python/test_linting.py tests/unit/plugins/python/test_typing.py tests/unit/plugins/python/test_testing.py -q`

Expected: all fixtures match explicit snapshots; no dependency presence is mislabeled as enforcement.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/python tests/fixtures/python/quality \
  tests/unit/plugins/python
git commit -m "Profile Python quality and unit test tooling"
```

## Task 5: Detect logging, observability, and configuration

**Files:**

- Create: `src/agentharness/plugins/python/logging.py`
- Create: `src/agentharness/plugins/python/observability.py`
- Create: `src/agentharness/plugins/python/configuration.py`
- Create: `tests/fixtures/python/runtime-quality/`
- Test: `tests/unit/plugins/python/test_logging.py`
- Test: `tests/unit/plugins/python/test_observability.py`
- Test: `tests/unit/plugins/python/test_configuration.py`

- [ ] **Step 1: Add failing semantic-depth fixtures**

Cover standard logging, structlog, Loguru, centralized/uncentralized config, context propagation, ad-hoc output, OpenTelemetry, Sentry, metrics/traces/health/error reporting, typed settings, environment loaders, `.env.sample`, schema validation, secret scanning, and mere unused imports.

- [ ] **Step 2: Observe the failure**

Run the three focused test files.

Expected: detectors are absent.

- [ ] **Step 3: Implement conservative evidence levels**

Report only the approved closed states: `absent`, `detected`, `configured`,
`executed`, and `enforced`. Avoid whole-program semantic claims from imports.
Recommendations vary by rigor and application type and preserve the existing
settings/logging stack.

- [ ] **Step 4: Verify no overclaiming**

Run: `python3 -m pytest tests/unit/plugins/python/test_logging.py tests/unit/plugins/python/test_observability.py tests/unit/plugins/python/test_configuration.py -q`

Expected: unused/import-only fixtures remain `detected` and never reach
`configured`, `executed`, or `enforced`.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/python tests/fixtures/python/runtime-quality \
  tests/unit/plugins/python
git commit -m "Profile Python runtime quality capabilities"
```

## Task 6: Detect mutation, documentation, and changelog tooling

**Files:**

- Create: `src/agentharness/plugins/python/mutation.py`
- Create: `src/agentharness/plugins/python/documentation.py`
- Create: `src/agentharness/plugins/python/changelog.py`
- Create: `tests/fixtures/python/project-quality/`
- Test: `tests/unit/plugins/python/test_mutation.py`
- Test: `tests/unit/plugins/python/test_documentation.py`
- Test: `tests/unit/plugins/python/test_changelog.py`

- [ ] **Step 1: Add failing fixtures**

Cover mutmut, Cosmic Ray, exclusions, CI placement, MkDocs, Sphinx, README-only, link/snippet/doc builds, monolithic changelog, Towncrier/fragments, and missing/ambiguous strategies.

- [ ] **Step 2: Observe the failure**

Run the three focused test files.

Expected: detector modules are absent.

- [ ] **Step 3: Implement detection and recommendations**

Mutation findings include expected cost and allowed gates. Documentation/changelog findings describe current strategy only; diff-aware enforcement remains a Slice 4 core responsibility.

- [ ] **Step 4: Verify fixture matrix**

Run focused tests and assert every fixture has an explicit expected outcome rather than a skip.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/python tests/fixtures/python/project-quality \
  tests/unit/plugins/python
git commit -m "Profile Python mutation and project documentation"
```

## Task 7: Compose recommendations and generated proposals

**Files:**

- Create: `src/agentharness/plugins/python/recommend.py`
- Create: `src/agentharness/plugins/python/plan.py`
- Create: `src/agentharness/plugins/python/verify.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/plugins/python/test_recommend.py`
- Test: `tests/unit/plugins/python/test_plan.py`
- Test: `tests/integration/test_recommendations.py`

- [ ] **Step 1: Write failing composition/conflict tests**

Assert recommendations are optional, detected mandatory baselines are preserved, incompatible stacks produce questions/conflicts, generated changes declare ownership/merge strategy, and accepted requirements verify through the same plugin.

- [ ] **Step 2: Observe the failure**

Run the focused unit/integration tests.

Expected: composition modules are missing.

- [ ] **Step 3: Implement deterministic composition**

Sort recommendations by stable ID, include positive/negative impact and cost,
and never modify files directly. Generated defaults use `create`,
`managed-block`, `structured-merge`, or `proposal-only` exactly as declared.
Wire `recommend [--json]` and plugin-backed bootstrap discovery/verification
through `cli.py` with stable result codes.

- [ ] **Step 4: Verify complete plugin contract**

Run: `python3 -m pytest tests/contract tests/unit/plugins/python tests/integration/test_recommendations.py -q`

Expected: Python plugin passes every compliance rule and capability coverage is complete.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/plugins/python src/agentharness/cli.py tests/unit/plugins/python \
  tests/integration/test_recommendations.py tests/contract
git commit -m "Compose Python bootstrap recommendations"
```

## Task 8: Verify Slice 2 and update acceptance evidence

**Files:**

- Modify: `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run plugin and fixture gates**

```bash
python3 -m pytest tests/contract tests/unit/plugins tests/integration/test_recommendations.py \
  --cov=agentharness.plugins --cov-branch --cov-fail-under=80
ruff check src/agentharness/plugins tests/contract tests/unit/plugins
mypy src/agentharness/plugins
bash tools/check.sh
```

Expected: all pass; no unexpected skip.

- [ ] **Step 2: Update evidenced acceptance rows**

Mark AC-04, AC-05, AC-19, and the plugin portions of AC-15 through AC-18 `implemented`. Keep E2E-dependent rows short of `verified`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md CHANGELOG.md
git commit -m "Record Python plugin implementation evidence"
```
