---
date: 2026-09-06
status: approved
topic: doc-ownership-gate
purpose: Design an optional gate that requires a PR touching a mapped code path to also touch the documentation that owns it.
related-harness: tools/check-completion.sh, tools/setup/harness-link.sh, src/agentharness/bootstrap/
---

# Doc-ownership gate design

## Status

Approved interactively on 2026-09-06. Follows up on issue #320, itself
prompted by PR #314's fix landing in one PR while its documentation
cleanup landed separately, days later, in #315/#316.

## Problem

Doc staleness in this repo currently relies on two things: the
`content-quality` gate's generated-file drift check (covers AGENTS.md,
MANIFEST.md, and the client adapters specifically — files derived
mechanically from a structured source) and human discipline for
everything else. There is no general "you changed behavior, did you
touch the doc that describes it" gate. Nothing catches a PR that changes
`tools/setup/harness-link.sh`'s behavior without touching
`docs/INTEGRATION.md`, for example — that drift is only caught later, if
at all, by someone independently noticing the docs are wrong.

## Goals

- Catch doc drift at review time for a defined set of code paths, not
  after the fact.
- Grow the mapped surface organically from what's actually touched,
  rather than requiring the whole existing tree to be mapped upfront.
- Give the operator an explicit, auditable way to say "this change
  genuinely needs no doc update" without a global on/off switch.
- Prove the mechanism on this repo before offering it to consumers.

## Non-goals

- Semantic verification that a touched doc actually describes the code
  change correctly — this gate only checks that the owning doc appears
  in the diff, the same shallow-but-useful bar `content-quality`'s other
  checks use.
- A generic doc-freshness or link-rot mechanism — that's already covered
  by `markdown-links` (CI) and `link-check-scheduled.yml` (weekly online
  check), which are unrelated recurring-maintenance-loop concerns.
- Retroactively mapping the entire existing codebase in one pass.

## Design

### 1. Ownership map — `DOC_OWNERSHIP.yaml`

A single YAML file at the repo root. A list of entries:

```yaml
- paths:
    - "tools/setup/harness-link.sh"
  docs:
    - "docs/INTEGRATION.md"
    - "MANIFEST.md"
- paths:
    - "src/agentharness/bootstrap/*.py"
  docs:
    - "docs/superpowers/specs/2026-07-14-project-bootstrap-policy-design.md"
```

`paths` are glob patterns matched against changed files. `docs` lists one
or more doc paths — touching *any one* of them satisfies that entry. A
single changed file may match more than one entry; all matching entries'
`docs` lists are unioned before checking satisfaction.

**Auto-exempt, never need an entry:**
- Test paths: `tools/tests/**`, `tests/**`, and other fixture/test globs.
- `*.md` files themselves (a doc can't need to own its own change).
- `DOC_OWNERSHIP.yaml` itself.

### 2. Enforcement in this repo's completion gate

A new script, `tools/verify-doc-ownership.py`, named consistently with
`tools/verify-content-quality.py` and `tools/verify-manifest.sh`. Wired
into `tools/check-completion.sh` as a new gate (`doc-ownership`),
always-on once merged — not itself behind a toggle in this repo, the
same way `ruff-core`/`mypy-core`/etc. aren't individually optional here.

Algorithm:

1. Resolve `merge-base(origin/main, HEAD)`. If it can't be resolved
   (shallow clone, no `origin/main`), **fail closed** with a clear
   message — never silently pass.
2. `git diff --name-only <merge-base>..HEAD` for the full branch's
   changed files (not just the latest commit — a doc update landing in
   an earlier commit on the same branch still satisfies a later commit's
   code change).
3. Drop auto-exempt paths (§1).
4. Parse `DOC_OWNERSHIP.yaml`. Malformed YAML **fails closed** with a
   parse error, not a silent skip.
5. For each remaining changed path:
   - No matching `paths` entry → **fail**: `"<path> has no
     DOC_OWNERSHIP.yaml entry — add one before this can pass."`
   - Matching entry, none of its unioned `docs` in the changed-file set,
     and no `Docs-not-needed:` trailer anywhere in the branch's commit
     range (§3) → **fail**, naming the path and its required doc(s).
   - Otherwise → pass.
6. Report all failures together in one pass, not fail-fast on the first.

### 3. Escape hatch — `Docs-not-needed:` trailer

A git trailer, e.g.:

```
fix: tighten retry backoff jitter bounds

Docs-not-needed: internal timing tweak, no documented behavior change
```

Presence of at least one `Docs-not-needed:` trailer anywhere in the
branch's commit range (the same range diffed in §2.2) exempts *all*
currently-failing mapped paths for that branch. This is a blanket,
branch-scoped override, matching the existing
`AGENTHARNESS_PR_MERGE_BYPASS` style: a visible, `git log`-auditable
human decision, not a silent skip and not a per-path surgical exemption.
This keeps the check's scope (whole-branch diff) and the escape hatch's
scope consistent with each other.

### 4. Consumer rollout — bootstrap question and `harness-link.sh` flag

Deferred until §2–3 are proven on this repo, but designed now so the
two entry points converge on one implementation rather than drifting
into two:

- **`agentharness bootstrap`**: a new standalone question,
  `docs.ownership`, in the style of the existing `publish` question
  (`src/agentharness/bootstrap/plan.py`) — not the `adopt.*`
  capability-scaffold pattern, since this is a policy choice rather than
  a detected-capability starter config. Prompt: "Enable doc-ownership
  enforcement? PRs touching a mapped code path must also touch its
  owning doc. (yes/no)", default `no`. A `yes` answer produces a
  `PlanAction` that scaffolds a minimal (effectively empty)
  `DOC_OWNERSHIP.yaml` at the consumer project's root and wires
  `verify-doc-ownership.py` into the generated `.agentharness-bin/check`
  wrapper — the same wrapper `enforce-profile` already runs through for
  `link`/`submodule`/`npm` modes.
- **`harness-link.sh init --with-docs-check`**: a new flag, in the style
  of `--with-hook`/`--with-coverage-hook`, for scripted/non-interactive
  init. Triggers the identical scaffold-and-wire action as the bootstrap
  `yes` answer — one action, two triggers.
- **Copy mode**: no live harness checkout to delegate to, so no wrapper
  exists there — same caveat `--with-coverage-hook` already carries, and
  already surfaced via `audit --json`'s `can_mechanically_enforce` field
  rather than a new reporting mechanism.

## Error handling

- Missing/unresolvable merge-base → fail closed, explicit message naming
  what couldn't be resolved.
- Malformed `DOC_OWNERSHIP.yaml` → fail closed with the YAML parser's
  error, not a silent pass-through.
- A `paths` glob matching zero files currently in the repo is not an
  error (it's normal for an entry to describe a path that hasn't changed
  in a given branch).

## Testing

- Unit tests for `tools/verify-doc-ownership.py`, mirroring
  `tools/tests/test_verify_content_quality.py`'s structure: fixture
  repos/branches covering — mapped path with doc touched (pass), mapped
  path with doc untouched and no trailer (fail), mapped path with doc
  untouched and a `Docs-not-needed:` trailer present (pass), unmapped
  path (fail, names the path), auto-exempt test/doc paths (pass without
  needing an entry), multi-entry union satisfaction, malformed YAML
  (fail closed), unresolvable merge-base (fail closed).
- ≥80% branch coverage, per this repo's existing gate convention
  (`pytest-coverage` in `tools/check-completion.sh`).
- Bootstrap-side: a `plan.py` test exercising the new `docs.ownership`
  question/action pair, mirroring existing `publish`/`rigor.tier`
  coverage.

## Out of scope / Future work

- The exact seed content (if any) for a freshly-scaffolded
  `DOC_OWNERSHIP.yaml` beyond "minimal/empty" — left to implementation,
  since over-guessing entries for an existing tree risks more noise than
  value.
- Per-path (rather than whole-branch) scoping for the `Docs-not-needed:`
  trailer, if blanket-branch exemption proves too coarse in practice.
- A CI-side (not just local completion-gate) copy of this check — not
  requested; the completion gate's Stop-hook enforcement was chosen
  specifically over a separate CI job for this repo's own use.
