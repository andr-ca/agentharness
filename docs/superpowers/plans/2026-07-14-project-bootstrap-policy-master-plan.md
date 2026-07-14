# Project Bootstrap Policy Implementation Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and dogfood a deterministic first-use project bootstrap system that discovers project quality capabilities, compiles an approved policy, and enforces it consistently at commit, push, CI, and agent-completion gates.

**Architecture:** The existing Node launcher invokes a versioned Python zipapp using a pinned `python-build-standalone` runtime. A Python core owns lifecycle, policy, evidence, transactions, and adapters; capability plugins return data through a versioned contract. Consumer repositories commit policy and bootstrap trust material under `.agentharness-policy/`, while caches and evidence remain under `.agentharness-local/`.

**Tech Stack:** Node.js 18+ launcher and base-trusted bootstrapper, CPython 3.12 `python-build-standalone` install-only runtime, Python zipapp, PyYAML safe loader, fastjsonschema, pytest, pytest-cov, Hypothesis, Ruff, mypy, mutmut, Bats, GitHub Actions, and GitHub REST/GraphQL APIs.

---

## Authority and source documents

- Design authority: `docs/superpowers/specs/2026-07-14-project-bootstrap-policy-design.md`
- Acceptance authority: `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md`
- Existing lifecycle implementation: `bin/cli.js` and `tools/setup/harness-link.sh`
- Existing profile compatibility surface: `patterns/profiles/` and `.agentharness-profile`
- Existing verification entry point: `tools/check.sh`
- Existing CI integration: `.github/workflows/ci.yml`
- Agent-policy canonical source: `CLAUDE.md`; generated clients must use the existing generators.

The design specification wins if a task summary below is ambiguous. Changing a design decision requires a spec amendment and review before implementation continues.

## Required implementation skills

- Use `@superpowers:test-driven-development` for every production change.
- Use `@python-conventions` for Python implementation and review.
- Use `@error-handling` for transaction, subprocess, artifact, and remote recovery paths.
- Use `@branching` and `@committing` for each task branch and atomic commit.
- Use `@superpowers:verification-before-completion` before every slice gate and publication claim.

## Scope decomposition

The design contains six dependent subsystems. Implement them in order using the linked plans:

1. [Core, schema, lifecycle, and reproducible runtime](2026-07-14-project-bootstrap-policy-slice-1-core.md)
2. [Plugin SDK and complete Python plugin](2026-07-14-project-bootstrap-policy-slice-2-plugins.md)
3. [Policy compiler, gates, and evidence](2026-07-14-project-bootstrap-policy-slice-3-policy.md)
4. [Core quality modules and generated integrations](2026-07-14-project-bootstrap-policy-slice-4-quality.md)
5. [GitHub protection, completion, and decommission](2026-07-14-project-bootstrap-policy-slice-5-github.md)
6. [Dogfooding, distribution, documentation, and release proof](2026-07-14-project-bootstrap-policy-slice-6-dogfood.md)

Do not begin a later slice until the previous slice's exit gate is green. A slice may expose an honest `unsupported` result for future behavior; it must never return a false pass.

## Locked implementation decisions

### Runtime packaging

Use Astral's `python-build-standalone` CPython
`3.12.13+20260510` `install_only_stripped.tar.gz` artifacts from immutable
release `20260510` as the initial self-contained interpreter. Pin exact
SHA-256/SHA-512 digests for these targets in
`runtime/python-build-standalone.lock.json`:

- `x86_64-unknown-linux-gnu`
- `aarch64-unknown-linux-gnu`
- `x86_64-apple-darwin`
- `aarch64-apple-darwin`

The artifact shape follows the upstream
[install-only archive contract](https://gregoryszorc.com/docs/python-build-standalone/main/distributions.html#install-only-archive),
and the initial filenames/digests must be read from the immutable
[`20260510` release](https://github.com/astral-sh/python-build-standalone/releases/tag/20260510),
not copied from an unversioned “latest” feed.

Build one platform-neutral `dist/agentharness.pyz` with the application and
exactly `PyYAML==6.0.3` and `fastjsonschema==2.21.2`. The build obtains the
hash-pinned PyYAML source distribution and copies only its `lib/yaml/`
pure-Python package (equivalent to upstream's `--without-libyaml` install), and
uses fastjsonschema's hash-pinned `py3-none-any` wheel. It rejects native
extensions and includes both licenses. The runtime archive and zipapp are
separate locked artifacts so mirrors can cache either without rebuilding.

The existing npm tarball remains the discovery/distribution entry point. It
includes the zipapp, artifact manifest, launcher, and bootstrap templates, but
not four large Python runtimes. `bin/cli.js` selects the locked target,
downloads it into a content-addressed cache, verifies SHA-512 before extraction,
and invokes the included zipapp. The base-committed CI bootstrapper independently
fetches both the exact npm tarball and selected runtime archive named in
`.agentharness-policy/runtime.lock`, verifies both SHA-512 values, securely
extracts them, and launches `package/dist/agentharness.pyz`; it never runs npm
lifecycle or untrusted head code.

The first dogfoodable package identity is `agentharness-toolkit@0.3.0-rc.1`
with matching Python core identity and Git tag `v0.3.0-rc.1`. Slice 6 changes
all three atomically before packing; the consumer lock is generated from those
exact packed bytes and the prerelease is verified from the registry before the
bootstrap proposal is applied.

The committed consumer lock is a schema-validated document with these required
sections:

- `package`: exact `agentharness-toolkit` version, registry URL, tarball URL,
  registry SRI string, normalized SHA-512, and allowed mirror URL.
- `zipapp`: path within the npm tarball, SHA-512, core version, schema version,
  bundled-plugin versions, and compatibility-provider version.
- `runtimes`: one entry per supported target with immutable upstream URL,
  SHA-256, SHA-512, archive prefix, and interpreter path.
- `acquisition`: selected target/source, mirror policy, size/member limits, and
  bootstrap protocol version.

`tools/runtime/build-runtime-lock.py` creates the lock only from a packed npm
tarball plus the reviewed upstream runtime manifest. The dependency-free
bootstrapper validates the lock schema, downloads the package and selected
runtime independently, verifies both before extraction, verifies internal
component identities against the lock, and only then launches the zipapp.

The bootstrapper is a dependency-free Node program using only `node:https`,
`node:crypto`, `node:zlib`, `node:fs`, and `node:path`. It parses the complete
tar metadata before writing, rejects absolute/traversal paths and every link
that does not resolve entirely within the verified member graph, enforces the
expected `python/` layout, and atomically promotes a verified cache directory.
No system Python, `pip`, `npm exec`, or shell `tar` is trusted during
authoritative acquisition.

The v1 bootstrap protocol caps each compressed artifact at 256 MiB, total
expanded bytes at 1 GiB, each regular member at 256 MiB, member count at
100,000, redirect count at 3, and path length at 4,096 UTF-8 bytes. It supports
USTAR regular files/directories, the pinned archives' relative symlink/hardlink
entries, and strictly parsed per-file PAX `path`/`size` metadata. Before writing
anything, it resolves the full link graph, rejects absolute/out-of-root/dangling
targets, cycles, chains deeper than 8, or terminals other than verified regular
files/directories, then creates validated links only after their targets. It
rejects devices, FIFOs, global PAX state, GNU long-name/link extensions, sparse
files, unknown type flags/metadata, duplicate destinations, and non-HTTPS
redirects outside the lock's approved source/mirror hosts.

### Python packaging and dependencies

Add a standard `src/agentharness/` package and `pyproject.toml`. Runtime
dependencies and artifact hashes live in `requirements-runtime.lock`;
development-only tools remain in `requirements-dev.txt`.
`tools/runtime/build-zipapp.py` assembles only those verified pure-Python
payloads in a temporary staging directory, rejects native extensions, copies
`src/agentharness`, writes the zipapp entry point, includes dependency licenses,
and produces a reproducible archive with normalized timestamps and file order.

### Compatibility boundary

Do not rewrite the Bash lifecycle in one change. `bin/cli.js` becomes a launcher
for the locked Python core for every public command; the core may invoke
`tools/setup/harness-link.sh` through a typed internal adapter for legacy asset
installation/update work. Python owns orchestration, policy, status, gates,
evidence, and result semantics. The compatibility provider imports
`.agentharness-profile` and existing Go, Node test, and Vitest enforcement until
committed requirements replace them. Unsupported migration uses only the
schema-defined `legacy-deferred` state with locked legacy path/hash/command;
undeclared dual-profile coexistence fails validation.

### Network boundary

The core uses Python standard-library HTTP for GitHub REST calls and GraphQL requests, with tokens read from `GH_TOKEN`/`GITHUB_TOKEN` or delegated read-only discovery through `gh auth token`. It does not add an opaque GitHub SDK. All remote writes require an explicit confirmed plan, repository identity check, and post-write read-back.

## Target file map

```text
pyproject.toml                         Python package, lint, type, test configuration
requirements-runtime.lock             Exact pure-Python runtime dependency closure
runtime/python-build-standalone.lock.json
                                       Platform runtime URLs and immutable digests
src/agentharness/
  __init__.py                          Public version/schema constants
  __main__.py                          Zipapp entry point
  cli.py                               Command parser and stable exit/result codes
  errors.py                            Typed domain failures and remediation
  models.py                            Shared immutable records
  project.py                           Root, Git, environment, and path boundaries
  bootstrap/                           State machine, discovery, questions, transactions
  profile/                             Schemas, load/merge/migrate/diff/history
  plugins/                             Contract, registry, runner, bundled providers
  policy/                              Compile, scope, verify, classify, evidence
  gates/                               Commit, push, CI, completion contexts
  integrations/                        Hooks, workflows, CODEOWNERS, agent-source generation
  remote/github/                       API, protection, review, completion, decommission
  schemas/                             Versioned JSON schemas shipped in the zipapp
templates/bootstrap/verify-runtime.mjs Base-trusted artifact fetch/extract/launch program
tools/runtime/                         Reproducible zipapp/runtime-lock build and verification
tests/unit/                            Focused deterministic unit tests
tests/contract/                        Shared plugin compliance suite
tests/fixtures/                        Python, repository, migration, and malformed fixtures
tests/integration/                     Disposable Git repositories and fake GitHub service
tests/e2e/                             Explicitly authorized real GitHub sandbox tests
```

Keep modules focused. A production module over roughly 400 lines should trigger a split-by-responsibility review rather than accumulating unrelated behavior.

## Cross-slice rules

- Follow test-driven development: failing focused test, observed failure, minimal implementation, focused pass, broader pass, commit.
- Use immutable dataclasses or equivalent typed records at boundaries; do not pass unvalidated dictionaries across subsystems.
- Execute project commands as argument arrays with `shell=False`; shell syntax is allowed only for an explicitly declared, user-approved shell requirement.
- Treat paths, repository config, plugin data, tar members, Git output, API data, and command output as untrusted.
- Every machine result has a stable code, JSON representation, human summary, and remediation.
- Never accept `error` as `pass`; strict mode fails closed.
- New generated artifacts carry generator/core/schema versions and a content hash.
- Tests that assert security behavior must include the corresponding negative case.
- Update the acceptance matrix evidence column in the same commit that implements a criterion. Evidence may not be marked verified until its test or read-back actually passes.
- Make one logical commit per task. Do not combine unrelated cleanup with policy reduction support.

## Program-level verification commands

Run the common commands whose paths exist at the current slice boundary, plus
the exact commands in that slice's final task:

```bash
python3 -m pytest tests/unit tests/integration -q
python3 -m pytest tests/unit tests/integration \
  --cov=agentharness --cov-branch --cov-fail-under=80
ruff check src tests tools/runtime
mypy src tools/runtime
bats .github/hooks/tests/ tools/tests/
bash tools/check.sh
npm pack --dry-run
```

Starting with Slice 2, add `tests/contract` to both pytest commands. Starting
with Slice 6 Task 1, also run
`python3 tools/acceptance/verify-matrix.py --completed-slice <n>`. Expected:
every applicable command exits `0`; no criterion required by the completed
slice is unmapped, missing, or failed. Future-slice paths are not silently
skipped; they become required at the slice that creates them.

At the release boundary also run:

```bash
python3 -m pytest tests/e2e -m github_sandbox -v
mutmut run --paths-to-mutate=src/agentharness --tests-dir=tests/unit
bash tools/acceptance/run-dogfood.sh
bash tools/acceptance/run-packed-artifact.sh
```

Expected: authorized sandbox passes, no unreviewed surviving mutant in security/policy modules, dogfood completes a real PR lifecycle, and a clean consumer bootstraps exclusively from verified packed artifacts.

## Milestone gates

### Gate A: Core runnable

- Slice 1 tests and coverage pass.
- `node bin/cli.js bootstrap --help` launches through the locked runtime.
- Invalid runtime digest and hostile tar fixtures fail before extraction/execution.
- An interrupted local bootstrap resumes deterministically.

### Gate B: Discovery credible

- Slice 2 plugin contract and fixture matrix pass.
- Every approved capability category produces typed findings with confidence and provenance.
- Existing runnable commands bind automatically; recommendations remain optional.
- Go/Node/Vitest compatibility fixtures retain prior enforcement.

### Gate C: Enforcement coherent

- Slices 3 and 4 pass.
- Commit, push, CI, and completion plans derive from one effective-policy hash.
- Evidence invalidates on every specified material input.
- Documentation/changelog classification remains diff-bound after rebase.
- Generated integrations contain plumbing only, never copied requirements.

### Gate D: Remote protection real

- Slice 5 fake-adapter integration tests pass.
- The authorized GitHub sandbox proves apply/read-back, review semantics, check identity, recovery, and three-PR decommission behavior.
- Strict activation refuses repositories where the required identity boundary cannot be expressed.

### Gate E: Release candidate

- Slice 6 dogfood passes all 31 acceptance criteria.
- Existing `tools/check.sh` remains green.
- Packed npm artifact bootstraps a clean Python fixture without the source checkout or system Python.
- Operator and user documentation distinguishes designed, preview, and generally available behavior.
- Runtime and gate latency measurements are recorded with agreed budgets.

## Evaluation scorecard

Release requires an overall score of at least 85/100, with correctness and security as hard gates:

| Dimension | Weight | Required result |
|---|---:|---:|
| Deterministic correctness | 20 | At least 18; no false pass |
| Security and non-weakening | 20 | At least 19; no critical/high open finding |
| Compatibility and migration | 15 | At least 13.5 |
| Bootstrap usability | 15 | At least 12 |
| Recovery and diagnostics | 10 | At least 8.5 |
| Distribution and portability | 10 | At least 9 |
| Maintainability and plugins | 5 | At least 4 |
| Documentation | 5 | At least 4.5 |

Record results in `docs/operational/reviews/project-bootstrap-release-evaluation.md` with an ISO 8601 datestamp. A weighted score cannot waive a hard gate or an unverified acceptance criterion.

## Execution sequence

- [ ] **Step 1: Execute Slice 1**

Follow `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-1-core.md` through its exit gate.

- [ ] **Step 2: Execute Slice 2**

Follow `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-2-plugins.md` through its exit gate.

- [ ] **Step 3: Execute Slice 3**

Follow `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-3-policy.md` through its exit gate.

- [ ] **Step 4: Execute Slice 4**

Follow `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-4-quality.md` through its exit gate.

- [ ] **Step 5: Execute Slice 5**

Follow `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-5-github.md` through its exit gate.

- [ ] **Step 6: Execute Slice 6**

Follow `docs/superpowers/plans/2026-07-14-project-bootstrap-policy-slice-6-dogfood.md` through its exit gate.

- [ ] **Step 7: Run the release evaluation**

Run every program-level verification command, verify all acceptance-matrix rows, perform the usability sessions, and write the dated release evaluation.

- [ ] **Step 8: Commit the evaluation**

```bash
git add docs/operational/reviews/project-bootstrap-release-evaluation.md \
  docs/superpowers/plans/2026-07-14-project-bootstrap-policy-acceptance-matrix.md
git commit -m "Document bootstrap policy release evidence"
```

Expected: the commit contains evidence/status changes only, and every `verified` claim names a reproducible artifact or remote read-back.
