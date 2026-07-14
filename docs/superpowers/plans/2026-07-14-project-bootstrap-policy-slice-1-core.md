# Project Bootstrap Policy Slice 1 Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a reproducibly packaged Python core with validated profiles, deterministic bootstrap states, resumable local transactions, and compatibility-safe command routing.

**Architecture:** A thin Node launcher selects and verifies a locked `python-build-standalone` runtime, then executes a reproducible Python zipapp. The Python core exposes typed JSON/human results and owns profile/state semantics; the existing Bash lifecycle remains the compatibility path for legacy commands.

**Tech Stack:** Node.js standard library, CPython 3.12 standalone runtime, Python zipapp, PyYAML, fastjsonschema, pytest, Hypothesis, Ruff, mypy, and Bats.

---

## Task 1: Create the typed Python command core

**Files:**

- Create: `pyproject.toml`
- Create: `requirements-runtime.lock`
- Modify: `requirements-dev.txt`
- Create: `src/agentharness/__init__.py`
- Create: `src/agentharness/__main__.py`
- Create: `src/agentharness/cli.py`
- Create: `src/agentharness/errors.py`
- Create: `src/agentharness/models.py`
- Test: `tests/unit/test_cli.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing CLI/result tests**

Test that `main(["status", "--json"])` returns stable JSON with `schema_version`, `code`, `outcome`, `summary`, `remediation`, and `details`; invalid commands return exit `2` without a traceback or secret-like environment content.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/test_cli.py tests/unit/test_models.py -q`

Expected: collection fails because `agentharness` does not exist.

- [ ] **Step 3: Implement the minimum typed core**

Use frozen dataclasses and enums for result codes/outcomes. Keep rendering separate from command execution. `__main__.py` must contain only `raise SystemExit(main())`.

- [ ] **Step 4: Verify focused quality**

Run: `python3 -m pytest tests/unit/test_cli.py tests/unit/test_models.py -q && ruff check src tests/unit/test_cli.py tests/unit/test_models.py && mypy src`

Expected: tests and static checks pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements-runtime.lock requirements-dev.txt src tests/unit
git commit -m "Build typed bootstrap command core"
```

## Task 2: Build a reproducible zipapp and locked runtime manifest

**Files:**

- Create: `runtime/python-build-standalone.lock.json`
- Create: `tools/runtime/build-zipapp.py`
- Create: `tools/runtime/build-runtime-lock.py`
- Create: `tools/runtime/verify-runtime-lock.py`
- Create: `tools/runtime/update-runtime-lock.py`
- Create: `src/agentharness/runtime_lock.py`
- Create: `src/agentharness/schemas/runtime-lock-v1.json`
- Test: `tests/unit/runtime/test_build_zipapp.py`
- Test: `tests/unit/runtime/test_runtime_lock.py`
- Modify: `package.json`

- [ ] **Step 1: Write failing reproducibility and lock tests**

Cover the complete consumer-lock schema, exactly four supported targets, HTTPS sources,
immutable release URLs, required SHA-256 and SHA-512, duplicate-target
rejection, hash-pinned PyYAML source and universal fastjsonschema wheel inputs,
dependency license inclusion, native-extension rejection, and byte-identical
zipapps from two builds with different temporary directories. The lock tests
must require exact npm name/version/registry/tarball/SRI/SHA-512, zipapp path and
digest, internal core/schema/plugin/provider versions, runtime target metadata,
mirror rules, archive limits, and bootstrap protocol version.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/runtime -q`

Expected: missing modules and lock file.

- [ ] **Step 3: Implement lock verification and zipapp build**

The builder must normalize timestamps/file modes/order; assemble
`PyYAML==6.0.3` from the verified sdist's `lib/yaml/` tree and
`fastjsonschema==2.21.2` from its verified universal wheel; include their
licenses; reject `.so`, `.dylib`, `.dll`, and executable dependency payloads;
and generate `dist/agentharness.pyz.sha512`. It must fail if any artifact hash,
package version, or expected file inventory differs from
`requirements-runtime.lock`.
`build-runtime-lock.py` must consume a real `npm pack --json` result and the
reviewed upstream runtime manifest, normalize npm's SRI to SHA-512, verify the
packed zipapp identity manifest, and emit the exact committed consumer lock.

- [ ] **Step 4: Verify repeatability**

Run: `python3 tools/runtime/build-zipapp.py --check-reproducible && python3 tools/runtime/verify-runtime-lock.py`

Expected: two build digests match and every runtime artifact entry validates.

- [ ] **Step 5: Commit**

```bash
git add runtime tools/runtime src/agentharness/runtime_lock.py \
  src/agentharness/schemas/runtime-lock-v1.json tests/unit/runtime package.json \
  dist/agentharness.pyz.sha512
git commit -m "Package reproducible bootstrap runtime"
```

Do not commit the generated binary zipapp unless the repository's release policy explicitly selects checked-in artifacts; publish/build it in CI and commit only its lock and expected digest.

## Task 3: Implement dependency-free secure artifact acquisition

**Files:**

- Create: `templates/bootstrap/verify-runtime.mjs`
- Create: `tools/tests/runtime-bootstrap.bats`
- Create: `tools/tests/fixtures/runtime-archives/README.md`
- Create: `tools/tests/helpers/make-runtime-fixtures.py`
- Test: `tests/unit/runtime/test_bootstrap_lock_contract.py`
- Modify: `tools/check.sh`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Generate hostile archives and write failing Bats tests**

Cover the pinned real runtime archives and separate valid npm/runtime fixtures,
including required in-root Python symlinks/hardlinks; wrong digest for either artifact,
lock/schema mismatch, internal identity mismatch, absolute paths, `..`, Windows
drive prefixes, escaping/dangling/cyclic/deep link graphs, device/FIFO, duplicate member, file/dir
collision, oversized member/archive/member count, truncated header/data,
unexpected top-level layout, cross-artifact path confusion, and cache changed
between verification and promotion.

- [ ] **Step 2: Observe the failure**

Run: `python3 tools/tests/helpers/make-runtime-fixtures.py && python3 -m pytest tests/unit/runtime/test_bootstrap_lock_contract.py -q && bats tools/tests/runtime-bootstrap.bats`

Expected: tests fail because the bootstrapper is absent.

- [ ] **Step 3: Implement safe download and tar-gzip extraction**

Use only Node standard-library modules. Load the base-committed consumer lock,
validate every field before network access, and hash each exact response body while
writing a temporary file; parse every tar header and resolve the complete member
and link graph before materialization; allow only relative in-root links whose
terminal target is a verified regular file/directory; enforce size/member
limits; extract regular content within a newly
created directory; verify the runtime archive's `python/` layout and the npm
tarball's `package/dist/agentharness.pyz` plus identity manifest; rename each
atomically to a digest-addressed cache; then launch only the two verified
artifacts together.

- [ ] **Step 4: Verify positive and adversarial paths**

Run: `python3 -m pytest tests/unit/runtime/test_bootstrap_lock_contract.py -q && bats tools/tests/runtime-bootstrap.bats`

Expected: every hostile archive fails before an outside file or executable appears; the valid fixture launches once and cache reuse re-verifies identity.

- [ ] **Step 5: Commit**

```bash
git add templates/bootstrap tools/tests/runtime-bootstrap.bats \
  tools/tests/fixtures/runtime-archives tools/tests/helpers/make-runtime-fixtures.py \
  tests/unit/runtime/test_bootstrap_lock_contract.py tools/check.sh .github/workflows/ci.yml
git commit -m "Verify runtime artifacts before execution"
```

## Task 4: Implement mirrors and dual-runtime upgrades

**Files:**

- Create: `src/agentharness/runtime.py`
- Create: `src/agentharness/runtime_upgrade.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/runtime/test_mirror.py`
- Test: `tests/integration/test_runtime_upgrade.py`

- [ ] **Step 1: Write failing mirror and upgrade-sequence tests**

Cover integrity-equivalent HTTPS/file mirrors, digest mismatch, unavailable
source, base runtime selecting/evaluating the candidate, candidate full
contract/migration execution, candidate self-report mismatch, schema-breaking
single-PR upgrade rejection, backward-compatible runtime PR followed by schema
PR, interrupted acquisition, and rollback to the base lock.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/runtime/test_mirror.py tests/integration/test_runtime_upgrade.py -q`

Expected: runtime mirror/upgrade modules are absent.

- [ ] **Step 3: Implement base-authoritative upgrade planning**

`agentharness runtime plan-upgrade` runs under the base-locked runtime, fetches
and verifies candidate package/runtime artifacts, compares internal identities,
runs the full plugin/schema/migration contract in an isolated process, and
produces a protected lock diff. The candidate never evaluates its own
admissibility. A mirror may replace only the source URL; every expected digest
and internal identity remains unchanged. A breaking schema change requires the
two-PR sequence described in the specification.

- [ ] **Step 4: Verify upgrade and rollback paths**

Run: `python3 -m pytest tests/unit/runtime/test_mirror.py tests/integration/test_runtime_upgrade.py -q`

Expected: equivalent mirrors pass, mismatches fail, and no fixture can move to
a schema the base runtime cannot assess.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/runtime.py src/agentharness/runtime_upgrade.py \
  src/agentharness/cli.py tests/unit/runtime/test_mirror.py \
  tests/integration/test_runtime_upgrade.py
git commit -m "Verify runtime mirrors and dual upgrades"
```

## Task 5: Add versioned profile schemas and non-weakening overrides

**Files:**

- Create: `src/agentharness/schemas/profile-v1.json`
- Create: `src/agentharness/schemas/local-override-v1.json`
- Create: `src/agentharness/profile/__init__.py`
- Create: `src/agentharness/profile/schema.py`
- Create: `src/agentharness/profile/loader.py`
- Create: `src/agentharness/profile/reduction.py`
- Test: `tests/unit/profile/test_schema.py`
- Test: `tests/unit/profile/test_loader.py`
- Test: `tests/unit/profile/test_reduction.py`

- [ ] **Step 1: Write failing schema and override property tests**

Generate valid profiles and mutations with Hypothesis. Assert unknown keys, duplicate IDs, invalid gates, invalid modes, non-canonical paths, executable/cache/runtime substitutions, threshold decreases, scope narrowing, and gate removal fail with stable codes.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/profile -q`

Expected: missing profile implementation.

- [ ] **Step 3: Implement parse, validate, normalize, and merge**

Use `yaml.safe_load`, reject aliases/custom tags and multiple documents, cap input size/nesting, validate JSON Schema, convert to typed records, canonicalize deterministically, then apply only allowlisted local presentation/performance fields. Never pass raw YAML dictionaries past the loader.

- [ ] **Step 4: Verify determinism and mutation resistance**

Run: `python3 -m pytest tests/unit/profile -q --hypothesis-show-statistics`

Expected: semantically equivalent profiles hash identically; every weakening mutation is rejected.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/schemas src/agentharness/profile tests/unit/profile
git commit -m "Validate committed bootstrap policy profiles"
```

## Task 6: Implement the bootstrap state machine and first-use behavior

**Files:**

- Create: `src/agentharness/project.py`
- Create: `src/agentharness/bootstrap/__init__.py`
- Create: `src/agentharness/bootstrap/state.py`
- Create: `src/agentharness/bootstrap/discovery.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/bootstrap/test_state.py`
- Test: `tests/integration/test_first_use.py`
- Test: `tests/integration/test_activation.py`

- [ ] **Step 1: Write failing state-transition tables**

Cover `unbootstrapped`, `discovered`, `awaiting-confirmation`, `locally-applied`, `proposal-open`, `default-branch-pending`, `remote-incomplete`, `active`, and `repair-required`. Include interactive first use, non-interactive CI failure, initial-proposal mode, exact default-branch SHA, and protection read-back predicates.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/bootstrap/test_state.py tests/integration/test_first_use.py tests/integration/test_activation.py -q`

Expected: missing state machine.

- [ ] **Step 3: Implement pure transition logic and environment detection**

State calculation must be a pure function of committed profile/history, local transaction record, CI event, default-branch evidence, and remote read-back. Do not commit a mutable `active: true` flag or require a second status commit.

- [ ] **Step 4: Verify table coverage**

Run: `python3 -m pytest tests/unit/bootstrap/test_state.py --cov=agentharness.bootstrap.state --cov-branch --cov-fail-under=80 -q`

Expected: the transition function meets the repository's Production-tier branch-coverage floor.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/project.py src/agentharness/bootstrap tests/unit/bootstrap \
  src/agentharness/cli.py tests/integration/test_first_use.py \
  tests/integration/test_activation.py
git commit -m "Model deterministic bootstrap activation"
```

## Task 7: Add reviewable plans and resumable local transactions

**Files:**

- Create: `src/agentharness/bootstrap/questions.py`
- Create: `src/agentharness/bootstrap/transaction.py`
- Create: `src/agentharness/profile/history.py`
- Modify: `src/agentharness/cli.py`
- Test: `tests/unit/bootstrap/test_questions.py`
- Test: `tests/unit/bootstrap/test_transaction.py`
- Test: `tests/integration/test_confirmation.py`
- Test: `tests/integration/test_local_recovery.py`

- [ ] **Step 1: Write failing confirmation and fault-injection tests**

Assert discovery is read-only; unresolved questions block apply; confirmation binds a canonical plan hash; writes detect TOCTOU changes; each write boundary can fail and resume; unfamiliar content is not overwritten; rollback restores exact bytes/modes.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/bootstrap/test_questions.py tests/unit/bootstrap/test_transaction.py tests/integration/test_confirmation.py tests/integration/test_local_recovery.py -q`

Expected: transaction classes are absent.

- [ ] **Step 3: Implement plan/confirm/apply/resume**

Persist recovery data only under `.agentharness-local/transactions/<id>/`; use same-filesystem temporary files plus atomic replace; fsync files/directories where supported; record redacted operations and hashes, never credentials or environment values.

- [ ] **Step 4: Verify all injected failures**

Run: `python3 -m pytest tests/integration/test_local_recovery.py -q`

Expected: every boundary ends in exact rollback or deterministic resumable state.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/bootstrap src/agentharness/profile/history.py \
  src/agentharness/cli.py tests/unit/bootstrap tests/integration/test_confirmation.py \
  tests/integration/test_local_recovery.py
git commit -m "Apply bootstrap plans as resumable transactions"
```

## Task 8: Preserve legacy profiles and route commands safely

**Files:**

- Create: `src/agentharness/profile/migrate.py`
- Create: `src/agentharness/plugins/compatibility.py`
- Modify: `src/agentharness/cli.py`
- Modify: `bin/cli.js`
- Modify: `tools/setup/harness-link.sh`
- Test: `tests/unit/profile/test_migrate.py`
- Test: `tests/integration/test_legacy_migration.py`
- Test: `tests/integration/test_legacy_coexistence.py`
- Test: `tests/integration/test_cli_routing.py`
- Test: `tools/tests/harness-lifecycle.bats`
- Test: `tools/tests/enforce-profile.bats`

- [ ] **Step 1: Write failing migration and routing tests**

Assert every public npm command reaches the verified Python runtime; Python may
delegate installation-only work to Bash but retains orchestration and result
semantics. Assert `init` performs legacy asset installation and then starts
bootstrap, `plan` previews both, policy-aware `status`/`doctor` aggregate install
and enforcement state, and `enforce-profile` invokes the locked compatibility
provider. Verify `.agentharness-profile` imports tier/coverage data with
provenance; Go/Node/Vitest remain mandatory; unsupported ecosystems enter
`legacy-deferred`; and active-policy uninstall directs the operator to protected
decommission.

Also cover the only valid two-file state: a declared `legacy-deferred`
requirement containing the legacy selector path/hash and locked provider
command/path/hash. Undeclared coexistence, changed legacy inputs, conflicting
free-form precedence, or unstructured path exceptions must block. Recognized
path exceptions import into structured scopes. Removal is allowed only when an
equivalent production plugin proves every enforced check.

- [ ] **Step 2: Observe the failure**

Run: `python3 -m pytest tests/unit/profile/test_migrate.py tests/integration/test_legacy_migration.py tests/integration/test_legacy_coexistence.py tests/integration/test_cli_routing.py -q && bats tools/tests/harness-lifecycle.bats tools/tests/enforce-profile.bats`

Expected: Python migration tests fail; existing Bats tests remain green.

- [ ] **Step 3: Implement migration and dispatch**

Make `bin/cli.js` a launcher only: every known command starts the verified
Python core. Add a typed internal legacy adapter in `cli.py` that invokes
`tools/setup/harness-link.sh` only for asset installation/update/generation
steps. `init` runs the legacy install transaction and immediately enters
bootstrap; `plan` composes both dry-run plans; `status`, `doctor`, `audit`, and
`enforce-profile` are core commands that incorporate legacy state/provider
results. `generate-clients` and non-policy `update` may delegate internally.
`uninstall` delegates only when no active policy exists; otherwise it returns
the decommission command. Direct script users retain the Bash interface, but
Bash never decides new policy, gates, evidence, or precedence.

Implement the `legacy-deferred` schema/state, locked legacy material inputs,
dual-profile validation, migration-removal proof, precedence audit, and
structured path-exception import. Explicit session instructions may strengthen
the effective request; any weakening requires a committed change or waiver.

- [ ] **Step 4: Verify compatibility matrix**

Run: `python3 -m pytest tests/unit/profile/test_migrate.py tests/integration/test_legacy_migration.py tests/integration/test_legacy_coexistence.py tests/integration/test_cli_routing.py -q && bats tools/tests/harness-lifecycle.bats tools/tests/enforce-profile.bats`

Expected: all pass; npm commands use one locked core, legacy Bash behavior is
preserved behind its adapter, and no ambiguous coexistence or precedence case
receives a pass.

- [ ] **Step 5: Commit**

```bash
git add src/agentharness/profile/migrate.py src/agentharness/plugins/compatibility.py \
  src/agentharness/cli.py bin/cli.js tools/setup/harness-link.sh tests tools/tests
git commit -m "Bridge legacy lifecycle into bootstrap core"
```

## Task 9: Verify Slice 1 and update acceptance evidence

**Files:**

- Modify: `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run the slice suite**

```bash
python3 -m pytest tests/unit tests/integration \
  --cov=agentharness --cov-branch --cov-fail-under=80
ruff check src tests tools/runtime
mypy src tools/runtime
bats tools/tests/runtime-bootstrap.bats tools/tests/harness-lifecycle.bats \
  tools/tests/enforce-profile.bats
bash tools/check.sh
npm pack --dry-run
```

Expected: every command exits `0`.

- [ ] **Step 2: Update only evidenced rows**

Mark AC-01, AC-02, AC-06 through AC-10, AC-12's local/runtime portion,
AC-13's acquisition portion, AC-16's migration/coexistence portion, AC-23's
local portion, AC-29's build portion, and AC-30's local namespace portion
`implemented`. Record mirror and dual-upgrade tests as supporting AC-13. Do not
mark them `verified` before later remote/packed-artifact proof.

- [ ] **Step 3: Commit the slice gate**

```bash
git add docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md CHANGELOG.md
git commit -m "Record core bootstrap implementation evidence"
```
