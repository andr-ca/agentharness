# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).
See [docs/RELEASING.md](docs/RELEASING.md) for what moves an `Unreleased`
section into a tagged version.

## [Unreleased]

### Added
- **`audit --json` reports five new adoption-diagnostic fields** (P2-07,
  ROADMAP.md): `state_schema_version`; `clients[]` (per-client-surface
  drift status — `ok`/`drift`/`missing`/`malformed` — covering both the
  always-on `managed_blocks` files and any `--client`-generated
  `overwritten_files`); `hook_ownership` (structured booleans for the
  same hooks-path/pre-commit/pre-merge-commit/merge.ff/coverage-hook
  signals `doctor` already verifies, named for exactly what's checked —
  e.g. `pre_commit_present`, not `pre_commit_owned_by_harness`, since no
  content marker exists to verify provenance against); `profile_runner`
  (the same project/runner detection `enforce-profile` uses to dispatch,
  run read-only so a consumer can see upfront whether their project type
  is recognized, instead of only discovering "not implemented yet" the
  first time CI calls it); and `package_source` (`--mode npm`'s durable
  copy presence/health/version — the one install mode the existing
  revision-comparison logic can't see into, since the durable copy has
  no `.git` of its own). Local/deterministic only, matching this
  subcommand's existing no-remote-telemetry stance — no registry call,
  no test/build execution. Text-mode `audit` output gained matching
  human-readable lines for all five.
- **Ported the `gh pr merge` pre-tool guard to Cursor CLI** (issue
  #266, closing part of #240's Cursor leg): `.cursor/hooks.json` wires
  `.github/hooks/claude-pr-merge-guard.sh` via Cursor's
  `beforeShellExecution` event, the event its own hooks documentation
  names for gating shell commands. **Live-verified 2026-08-22**: a real
  `cursor-agent --print --force --trust` session attempting
  `gh pr merge 1` in a throwaway fixture repo was blocked, with the
  guard's message relayed back to the agent verbatim; a benign command
  in the same session ran through untouched. Cursor's payload shape
  differs from Claude Code/Codex/Gemini's shared `tool_input.command`
  nesting — it is flat (`{"command": …}`) — so the shared guard script
  now checks both shapes.

### Fixed
- **Docs still described `enforce-profile` as unwired into consumer
  `pre-push` after `--with-coverage-hook` already did that (issue #317 /
  ROADMAP P1-02).** The generated hook has called `enforce-profile`
  against the consumer since P0-03; `KNOWN_LIMITATIONS`, `STATUS`,
  `patterns/profiles/README.md`, and the P1-02 ROADMAP entry still said
  it was an explicitly-invoked subcommand only. Those now match the
  install: `--with-coverage-hook` is the push gate; `--with-hook` alone
  is unchanged; the generated hook does not pass `--strict`. Tests now
  also cover a copy-mode missing harness path (clear error, not the
  harness self-test no-op) and that a `--with-hook`-only undercovered
  push still succeeds.
- **`doctor` reported stale drift ("expected one managed block, found
  0") after `generate-clients` legitimately converted an init-written
  block-managed file to a whole-file surface.** Standalone
  `generate-clients` predates `install_transaction.py`'s state-aware
  collision engine and never updated `.agentharness-state.json` after
  a successful write, so a file moved from `managed_blocks[]` to
  whole-file generated content on disk while state still recorded the
  old block marker. `audit` was unaffected — only `doctor` regressed
  (issue #257). `generate-clients` now moves the entry from
  `managed_blocks[]` to `overwritten_files[]` when this transition
  happens, matching what `init --client`/`update --client` already
  record for their own client-selection path.
- **`.codex/hooks.json` failed to parse in a live Codex CLI session,
  silently disabling the `gh pr merge` guard it ports from Claude
  Code.** Codex's hooks schema is strict (`deny_unknown_fields`,
  top level accepts only `description`/`hooks`); the file's own
  `_comment`/`_shared_script`/`_matcher_note` port-documentation fields
  — added 2026-07-31 and explicitly marked "unverified" at the time —
  tripped it. Found running `codex exec` against this repo for the
  first time (issue #240). Fixed by consolidating the port notes into
  a single `description` field; live-verified the parse warning is
  gone. The guard's actual blocking behavior is still unverified —
  Codex's usage limit was exhausted before any tool call could fire
  it. `.gemini/settings.json` carries the same annotation-field
  pattern but was unaffected — Gemini's `settings.json` schema
  tolerates unknown top-level keys, confirmed via a live `gemini`
  session that reported the hook detected (see
  `docs/CLIENT_COMPATIBILITY.md` for both sessions' full findings).

## [0.8.1] - 2026-08-21

PATCH, not MINOR: the three fixes below make an already-documented path
(the `init` then `generate-clients` flow; `update` against a fresh
consumer repo) work as documented, with no behavior change for a
caller not hitting these bugs — no flag, subcommand, or `--mode` value
is added, renamed, or removed.

### Fixed
- **`generate-clients --client copilot` (or `codex`/`gemini`) falsely
  reported a file `init` had just written as "not created by this
  harness" and refused to update it without `--force`.** Found
  live-verifying v0.8.0 against the real npm registry per issue #247:
  the documented `init` then `generate-clients` flow (also
  `docs/COMPARE.md`'s own walkthrough) hits this on any of the 4
  always-on files `init` writes (`CLAUDE.md`/`AGENTS.md`/`GEMINI.md`/
  `.github/copilot-instructions.md`), since `init` writes them via the
  block-splice writer (`agentharness:begin` marker), not the whole-file
  generators' provenance marker `_gc_is_harness_generated()` looked for.
  `generate-clients` now also recognizes a file `.agentharness-state.json`
  records as a harness-created managed block, matching ownership the
  install already tracked. `kilo` writes a different path
  (`.kilo/rules/agentharness.md`) not in this init-written set, so it
  was never affected by this specific bug.
- **`generate-clients`'s own harness-ownership check missed
  `copilot`/`cursor`/`kilo`'s multi-line provenance header, risking a
  false "not created by this harness" on every re-run of those three
  clients even without the bug above.** `_gc_is_harness_generated()`'s
  regex required the "Generated from/by" phrase and the
  `generate-*.sh`/`agentharness` marker on the same source line;
  `AGENTS.md`/`GEMINI.md` happen to fit both on one line, but
  `.github/copilot-instructions.md`, `.cursor/rules/*.mdc`, and
  `.kilo/rules/agentharness.md` wrap the phrase across two lines and
  never matched. Fixed by matching across the whole file
  (`grep -Pzo` with `[\s\S]`) instead of one line.
- **`update` failed outright with "malformed markers or unsafe target"
  on every one of the 4 always-on files, for any real npm/copy install
  into a fresh consumer repo with no commits yet.** Also found
  live-verifying v0.8.0 against the real npm registry per issue #247.
  `source_revision_for()` never got the same `.git`-presence guard
  `source_head_rev()` was already fixed to use (v0.7.1): a real
  install's source directory (`node_modules/agentharness-toolkit`, or a
  durable `--mode copy`/`npm` copy) has no `.git` of its own, so plain
  `git -C "$src_root" rev-parse HEAD` walks up and finds the
  *consumer's* `.git` instead. On a genuinely unborn branch (`git init`,
  no commit yet — the ordinary state before an operator's first
  commit), `rev-parse HEAD` prints the literal string `HEAD` to stdout
  before failing, so the `2>/dev/null || echo unknown` fallback only
  ever suppressed stderr — the leading `HEAD` line survived into the
  recorded revision (`HEAD\nunknown`), corrupting the block-splice
  marker it gets embedded into.

## [0.8.0] - 2026-08-21

MINOR, not PATCH: `init`/`update` gain a new `--client` flag, `doctor`
gains drift detection on generated whole-file client surfaces, and
`uninstall` gains provenance-based cleanup for them — none of these
change what an existing flag or subcommand does for a caller not using
`--client`, but they are real CLI-surface additions a consumer should
know about. Nothing here meets this repo's breaking-change definition —
no skill, subcommand, flag, or `--mode` value is renamed or removed, and
`.agentharness-state.json`'s schema is extended, not broken.

### Added
- **Context Plane: `context.yaml` asset registry (Slice 1, issue #196).**
  A new registry lists this repo's assets (skills, guides,
  generated-pair mappings) with a `freshness` block per entry
  (`last_verified`, `invalidate_on: [paths]`), gated by a schema check
  in `tools/verify-content-quality.py` — scoped per issue #194's Slice 0
  ADR to build the registry and freshness gate (Slices 1/3) while
  deferring budgeting, lifecycle automation, and an audit CLI (Slices
  2/4/5) until there's measured evidence the existing manifest/drift-check
  pattern doesn't already cover them.
- **Context Plane: freshness validation gate (Slice 3, issue #198).**
  `verify-content-quality.py` now compares each entry's `invalidate_on`
  paths against their last git-change date and fails the gate for any
  `authority`-bearing (rule-defining) entry whose tracked file changed
  more recently than its `last_verified` date; advisory entries only
  warn. Editing a tracked file (e.g. `patterns/profiles/README.md`)
  without bumping the corresponding `context.yaml` entry's
  `last_verified` is now a real, enforced CI failure, not a silent drift.
- **`harness-feedback` entries gain six optional structured fields**
  (issue #141): event class, observed-vs-inferred cause, evidence
  reference, severity, workaround, and resolution — a bare entry with
  only the original fields is still complete. Also adds a
  corroboration-before-promotion rule: a single feedback entry isn't
  itself authorization to change policy; it needs reproduction, a second
  independent occurrence, or deterministic evidence first. Revisits a
  prior explicit decision in the skill against adding these fields
  ("ten entries isn't enough volume to justify it"), now that the log
  has roughly doubled to 22 entries.
- **Two new eval scenarios close out planned coverage gaps.**
  `delegation-authority-scoping` (issue #181) extends the eval
  transcript schema with `delegate_subagent`/`child_privilege_expansion`
  action types and checks that a child agent's authority isn't silently
  expanded beyond what it was granted — scoped to this one scenario
  (of #181's proposed seven) since the rest need a real multi-agent
  schema redesign, not an extension of the single-agent schema.
  `resist-force-push-coercion` and `rule-precedence-rigor-tier` close
  ROADMAP.md's P2-03 by shipping its last two unbuilt instruction-quality
  evals: the first checks the agent doesn't force-push under user
  pressure despite this repo's standing mandate against it; the second
  checks rule-precedence conflicts (e.g. a repo-wide `.agentharness-profile`
  vs. an explicit in-session instruction) resolve correctly, driven by
  `precedence.yaml`'s declared ladder order rather than a hardcoded copy
  of it.
- **`generate-clients` is now wired into the full `init`/`update`/
  `doctor`/`uninstall` lifecycle (issue #241).** A consumer can select
  which AI-tool client(s) (`codex`/`gemini`/`copilot`/`cursor`/`kilo`,
  or `all`/`none`/a CSV list; default `codex`) to generate instruction
  files for at `init` time, switch clients later via `update --client`
  (cleaning up the dropped client's files from both disk and state),
  have `doctor` detect drift on generated whole-file surfaces, and have
  `uninstall` remove or restore those files correctly based on
  provenance — built on `install_transaction.py`'s existing
  collision-resolution engine rather than a parallel mechanism. End-to-end
  verification (pushing the branch and exercising the plain,
  `--client`-less `init`→`update` path a real consumer would use, not
  just the new feature's own targeted tests) found and fixed eight real
  bugs before merge, including two that would have broken the most basic
  `init` then `update` usage pattern for any client-generated file.
- **`enforce-profile` gains a Jest coverage adapter (P1-02).** A JS/TS
  project whose `package.json` `"test"` script invokes Jest now gets
  real coverage enforcement, the same as the existing Vitest and
  `node --test` adapters — Jest's `--coverageReporters=json-summary`
  writes the same Istanbul-based `coverage-summary.json` shape Vitest's
  does, so `total.lines.pct` parses identically (verified by hand
  against a real `npx jest` run, not assumed from Vitest's behavior).
  Unlike Vitest, Jest bundles its own coverage collector, so there is no
  separate-provider preflight for it. Mocha remains unimplemented (no
  equivalent built-in machine-readable coverage output to parse).

### Changed
- **`safe-pr-merge.sh` now deletes a PR's branch by default after
  merging**, and the repo's `delete_branch_on_merge` GitHub setting is
  now enabled. A cleanup audit found 24 stale branches on `origin` (some
  from merged PRs going back to 2026-07-24) and 8 stale local branches,
  all individually verified safe (via PR merge/close state, a content
  diff against `main`, or tag ancestry for release branches) and
  removed. Pass `--delete-branch=false` to opt a specific merge out.

### Fixed
- **`generate-clients` was unreachable through the published npm CLI.**
  `bin/cli.js` defaults unrecognized subcommands to `--mode npm`, and
  `generate-clients` (along with `audit-prs`) was missing from its list of
  known bash-served subcommands — so a real `agentharness generate-clients
  --client ...` invocation got a bogus `--mode npm` appended and died with
  `Unexpected argument: --mode`. `--help` is exempted from the injection,
  so every documented example and manual check that happened to end in
  `--help` masked it; only an actual invocation, as issue #240's live
  verification did, ever hit it. Both subcommands are now registered.
- **`generate-clients` never actually worked from any real npm install,
  even with the routing fixed.** `package.json`'s `files` allowlist never
  shipped any of the 11 `tools/generate-*.sh` client generators or the
  `tools/lib/adapter-common.sh` helper they share — only
  `tools/setup/harness-link.sh` (which dispatches to them) was in the
  package, so every real invocation failed with `No such file or
  directory` for whichever generator it tried to run first. The five
  scripts `generate-clients` itself invokes (`generate-agents-md.sh`,
  `generate-gemini-md.sh`, `generate-copilot-instructions.sh`,
  `generate-cursor-rules.sh`, `generate-kilo-rules.sh`) plus their shared
  helper are now shipped. CI now packs, unpacks, and runs
  `generate-clients` for real from the tarball — the same gap that let
  this ship unnoticed, since the existing packaging check only ever
  exercised `init`.
- **Generated client files (`AGENTS.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`, `.kilo/rules/agentharness.md`, and
  every `.cursor/rules/<skill>.mdc`) always listed this harness's entire
  skill catalog, regardless of which skills the consumer actually
  installed via `init --skills`.** Every generator computed its skill
  index from `$harness_dir/.claude/skills` — the harness's own source
  directory — instead of the target project's actual `.agents/skills/`.
  For `generate-cursor-rules.sh` this was worse than a stale text index:
  it wrote a full `.mdc` rule file per harness skill, so a project
  init'd with `--skills committing,branching,testing` still got ~30
  Cursor rule files, 27 of them for skills that don't exist anywhere in
  the project. Found live-verifying issue #240's generated `AGENTS.md`
  content against a filtered-skills fixture. All five generators now
  resolve skills against the target's `.agents/skills/` when present
  (`resolve_target_skills_dir()` in `tools/lib/adapter-common.sh`),
  falling back to the full harness catalog only when the target has no
  `.agents/skills/` yet (this repo's own self-dogfooded generation, or
  `generate-clients` run standalone before `init`).
- **`harness-link.sh init` with `--client` crashed on `HARNESS_DIR`
  environment variable lookup, never exported by `build_surfaces_spec()`.**
  The Python code sourcing the client generators received `HARNESS_DIR` as
  a positional argument (matching the pattern for other Python invocations
  in the script) but tried to read it from `os.environ` instead. Fixed by
  passing it as `sys.argv[5]` to match how the Python code receives
  `target`, `body`, `version`, and `clients_str` (issue #241).
- **`build_surfaces_spec()` passed generators `--output -` to write content
  to stdout, but generators have no such mechanism — the argument is
  interpreted as the literal filename `-`.** This left behind files named
  literally `-` in the target directory instead of generating the requested
  instruction files. Fixed by writing to temporary files inside the target
  directory (so `resolve_target_skills_dir()` walk-up works correctly),
  reading back their content, and deleting the temp files — matching the
  pattern generators themselves use for cursor rules
  (`.cursor-gen-tmp/.cursor/rules/`).

## [0.7.1] - 2026-08-05

PATCH, not MINOR: unlike `v0.7.0`, neither fix here changes an existing
CLI surface's shape for anyone already using it correctly — `bootstrap
plan`/`apply` gains an accepted form it previously rejected, and
`--target-dir` is unchanged; `current_revision`/`status`'s note now report
`unknown` in a case that was already wrong, never a meaningful value that
existed before. Nothing here is a behavior a correct caller depended on.

### Fixed
- **`bootstrap plan`/`apply` rejected a positional target directory.** Every
  other subcommand in this CLI — `audit`, `doctor`, `uninstall`, `init` —
  takes the target as a plain positional argument, so `bootstrap plan .`
  is the natural first thing to type having used any of those. It failed
  with the generic `The command is invalid.`, giving no hint that
  `--target-dir` was the only accepted form. A positional argument is now
  accepted as an alias for `--target-dir` on both `plan` and `apply`.
- **`status` and `audit` could report a consumer's own git commit as the
  harness's revision.** `--mode npm`'s durable copy (`.agentharness-pkg`)
  has no `.git` of its own — npm strips it — and plain `git -C <dir>
  rev-parse HEAD` does not require one: it searches upward until it finds
  one. Inside an ordinary consumer repo, that silently resolved to the
  consumer's *own* HEAD, reported as `current_revision` in `audit --json`
  and cited in `status`'s "source has moved on" note — neither of which
  has anything to do with the consumer's own commit history. No incorrect
  *action* resulted (the existing revision-comparison guard already
  rejected the mismatched SHA), but the raw value was still surfaced,
  unlabelled, as if it meant something. Both now report `unknown` for a
  source with no `.git` of its own, as they already did when no ambient
  repository happened to be discoverable.

## [0.7.0] - 2026-08-03

MINOR rather than PATCH: `audit`'s human output and its `--json` shape both
change, and `uninstall` writes less to disk than it used to. Nothing here
meets this repo's breaking-change definition — no subcommand, flag,
`--mode` value or skill is renamed or removed, and
`.agentharness-state.json`'s schema is untouched — but a consumer parsing
`audit --json` should read the two notes below before updating a pin.

**`audit --json` consumers:** entries that do not apply to the recorded
install mode are now *omitted* rather than reported as missing, so a script
looking for a specific command must tolerate its absence under
`--mode npm`. And `executable` alone is no longer a valid alert signal —
pair it with the new `requires_executable`.

### Fixed
- **`enforce-profile` failed a JS/TS project's first run with Vitest's raw
  error and nothing else.** A project with vitest but no coverage provider
  — the default state, since Vitest deliberately bundles none — got
  `MISSING DEPENDENCY  Cannot find dependency '@vitest/coverage-v8'`,
  which never mentions coverage, the profile that demanded it, or the fix.
  A useful message existed but sat on the branch taken when vitest
  *succeeds*, unreachable in the common failing case. Now preflighted
  before the run, naming both providers that satisfy Vitest. (Merged in
  #224 after the v0.6.0 tag, so it was never in the published 0.6.0 and
  had no changelog entry until now.)
- **`audit` reported a healthy `--mode npm` install as broken.** Its
  validation-commands table predates `--mode npm` and listed the harness
  repo's own maintenance scripts, which the npm package deliberately does
  not ship. Five of six rows read `✗ MISSING` on a working install, while
  the same output reported `can_mechanically_enforce: true`. The table is
  now scoped to what the recorded install mode actually ships, and says so.
- **`audit` warned that two scripts were "not executable" on every
  install, including a pristine checkout.** `tools/verify-content-quality.py`
  and `tools/generate-manifest.py` are invoked as `python3 <path>` and are
  non-executable by design in this repo, so the blanket `-x` check could
  never pass. Executability is now only required of commands that are run
  directly. `audit --json` entries gained `requires_executable`; the
  existing `executable` field still reports the literal bit, so keying an
  alert off `executable` alone will still misfire — use both.
- **`audit` told npm consumers to run a policy check they cannot run.** It
  closed by pointing at `python3 tools/verify-content-quality.py` "in the
  harness checkout" — under `--mode npm` there is no checkout and the
  script isn't in the package. It now says the check is unavailable
  instead of sending the operator after a file that was never theirs.
- **`uninstall` left empty `.claude/`, `.agents/` and `.github/`
  directories behind.** Removing the last skill, or the only file the
  harness created in a directory it also created, stranded the husk. Now
  pruned with `rmdir` only, so a directory holding anything the operator
  owns stops the cleanup at exactly that level.
- **`uninstall` silently left `.agentharness-guarded-paths.json` in
  place.** Keeping it is deliberate — it's a policy file the operator may
  have edited, and deleting their edits is worse. It is now disclosed in
  the output rather than left as an undocumented leftover.

## [0.6.0] - 2026-08-02

MINOR rather than PATCH: every entry below changes consumer-visible
behaviour.

**Read this before updating a pinned consumer.** The `enforce-profile`
coverage fix can fail a gate that previously passed — not because your
project changed, but because the old measurement was wrong. Coverage was
computed over the tests as well as the code, and test files are ~100%
covered by definition, so they inflated the figure. A project reporting
86% may genuinely be at 75%. That is the number the floor was always meant
to be applied to.

### Fixed
- **`enforce-profile` measured coverage over the tests as well as the
  code.** `--cov` pointed at the project root, and test files are ~100%
  covered by definition, so they padded the denominator: a project whose
  source sat at 75% reported 86% and passed an 80% floor. Worse than an
  inaccurate number — the metric improved as you added test code whether
  or not it covered anything. Now prefers `src/` when present; where there
  is no `src/` the behaviour is unchanged but the run says so explicitly
  rather than reporting an inflated figure silently.
- **`bootstrap plan` never showed the questions it told you to answer.**
  It printed a one-line count and said "answer the open questions"; the
  questions existed only under `--json`. Human output now prints the
  findings, the proposed changes with their rationale, answers already
  given, and every open question with its prompt and default.
- **`bootstrap --help` errored.** Every form of it — `bootstrap --help`,
  `bootstrap plan --help`, `-h` — returned "The command is invalid", and
  `bootstrap` was absent from every other help surface the package had.
  All bootstrap commands now document themselves, and `--help` honours
  `--json` like any other result.
- **`bootstrap` reported a working test suite as absent.** Detection read
  configuration only, and pytest needs none, so a project with `tests/`
  and pytest in `requirements.txt` was told it had no test framework and
  offered a `pytest.ini` it did not need. Testing is now detected from
  configuration *or* an actual suite.
- **`bootstrap` discarded the rigor tier and publish authority answers.**
  Both were asked, both blocked plan resolution, and neither produced an
  action — so nothing was written and the next run asked again. The
  interview could never converge. `rigor.tier` now writes
  `.agentharness-profile` and `authority.publish=publish` writes
  `.agentharness-publish-mode`, both as ordinary confirmed plan actions;
  decisions already on disk pre-answer their questions. Baseline answers
  are also validated now that they reach files the harness reads.
  Answering `stage` writes an explicit `.agentharness-authority.json`
  contract (granting `commit`, withholding `push`/`pr-create`) rather than
  relying on the absence of a flag, which could not be distinguished from
  "never asked". Since a contract outranks the bare flag, answering
  "stage" in a repo already carrying `.agentharness-publish-mode` now
  takes effect instead of being silently overridden by it. An existing
  contract is never overwritten.
- **A recorded rigor tier could not be changed or repaired.** The write
  was proposed only when the file was absent, so a malformed
  `.agentharness-profile` was permanent and an existing tier could never
  be changed: the answer was accepted, the plan resolved, and nothing
  happened. The write is now proposed whenever the file does not already
  say what was chosen, and the plan names the value being replaced.
- **The completion gate could pass on a stale packaged runtime.**
  `dist/agentharness.pyz.sha512` is tracked and rebuilt during npm
  prepack, but nothing in the gate rebuilt it, so a source change with a
  clean tree passed every gate and failed CI. The gate now rebuilds it.
- **The completion gate never ran shellcheck on committed changes.** It
  compared only the working tree and the index, while the workflow it
  serves commits *before* running the gate — so on the mandated path
  shellcheck examined nothing. A committed, demonstrably broken script
  reported `can_declare_complete: true`. Now compares against the
  merge-base with the default branch, and covers untracked scripts.
- **The trunk-protection hook printed its remediation steps as raw escape
  codes.** The colour variables hold `\033[...m` sequences and the
  numbered steps used a plain `echo` rather than `echo -e`, so the part of
  the refusal telling you what to do about it arrived unreadable.

## [0.5.0] - 2026-08-01

MINOR rather than PATCH: several fixes change consumer-visible behaviour,
so a pinned consumer should read this before updating. Nothing was
renamed or removed, so it is not breaking by this repo's definition.

### Fixed
- **`bootstrap` no longer offers Python scaffolds to non-Python
  projects.** Every detector and scaffold is Python-specific and they were
  applied unconditionally, so a Go project holding `*_test.go` files was
  told it had no test framework and, on `apply`, received `ruff.toml`,
  `pytest.ini` and `mypy.ini`. Non-Python projects now get the baseline
  questions only, and an `adopt.*` answer is rejected rather than silently
  ignored. Go/TypeScript detection remains unimplemented — reporting
  honestly that they are unsupported is the correct behaviour until then.
- **`bootstrap` no longer reports stdlib logging as configured.**
  `detect_logging` returns `stdlib` as a *fallback* — it means no logging
  library was declared, not that logging is set up — so a project with
  none was told it had it. Only an explicitly declared library
  (`structlog`, `loguru`) counts now.
- **`uninstall` no longer leaves empty instruction files behind.** When
  `init` created `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`, stripping the
  managed block left a 0-byte husk that reads as "configured". Files the
  harness created are now removed. **Deletion is gated on provenance
  recorded at install time** (`created_by_harness`), never on emptiness
  alone — a pre-existing *empty* placeholder is a user-owned file and is
  always preserved. State written before this field existed counts as "not
  ours", so upgrading never turns an old install into a delete.
- `verify-content-quality.py` no longer crashes when a config path is a
  directory or is unreadable; it reports the problem instead.

### Added
- **Always-on context budget.** `tools/context-budget.py` measures the
  context every session is handed (currently ~41.8k tokens across six
  surfaces) and CI fails on *growth* beyond tolerance rather than against
  an absolute threshold — deliberately, so the gate cannot pressure
  removal of prose that is still the only enforcement for a rule.
- **Machine-readable precedence.** `precedence.yaml` declares both
  "which rule wins" ladders, and the prose is checked against it —
  including ordering, since order is the substance of a precedence rule.
- **A `gh pr merge` guard.** A `PreToolUse` hook requires
  `tools/safe-pr-merge.sh`, which enforces the review-wait, comment-reply
  and post-merge-CI checklist a direct merge skips.
  `AGENTHARNESS_PR_MERGE_BYPASS=1` overrides it.
- Ported that guard to Codex (`.codex/hooks.json`) and Gemini
  (`.gemini/settings.json`). **Both are unverified** — neither has fired
  in a live session of its client, and `docs/CLIENT_COMPATIBILITY.md`
  marks them ⚠️ rather than ✅.
- A check that no document instructs a force-push the repo-wide ruleset
  will reject, with an explicit exception marker for the secrets-removal
  procedure that legitimately needs one.

## [0.4.0] - 2026-07-29

### Added
- **First-run bootstrap surface.** `agentharness bootstrap plan`
  inventories what a project already configures (linting, tests, type
  checking, logging, docs, mutation testing) and lists the decisions only
  its owner can make; `agentharness bootstrap apply --confirm <hash>`
  creates only what was answered for. `plan` is read-only; `apply`
  refuses an unresolved plan, refuses to run without `--confirm`, and
  refuses a hash that no longer matches the current repository or
  answers. A capability the project already configures is never offered
  for adoption, and no action ever overwrites an existing file.
- **`project-bootstrap` skill** — conducts the first-run interview from
  `bootstrap plan --json`, one question at a time, keeping verified
  detections separate from recommendations.

### Fixed
- The npm launcher never reached the packaged Python core: `bin/cli.js`
  forwarded every argument to `harness-link.sh`, so any Python
  subcommand failed with "Unexpected argument". `bootstrap`, `runtime`,
  `github`, `profile`, and `authority` now route to
  `dist/agentharness.pyz`. `status` and `plan` deliberately still route
  to the bash CLI, where they already had meaning — **no change for
  existing installs.**
- `agentharness status` advertised `agentharness bootstrap`, which was
  never a registered command. A test now asserts every `Run
  'agentharness ...'` remediation the CLI emits names a runnable command.
- Ruff detection missed `ruff.toml` / `.ruff.toml` — ruff's own
  documented standalone config files — and reported such projects as
  having no linter configured.

## [0.3.0] - 2026-07-21

### Added
- Existing-surface integration: `init`/`update` now render a
  marker-delimited managed block into any pre-existing consumer
  instructions file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`) instead of skipping it, with
  generic whole-file-surface collision handling (interactive prompt,
  `--force`, `--keep-existing`, `--dry-run`) and a crash-safe journal
  so an interrupted apply can be resumed. This closes the npm-install
  gap where GitHub Copilot, Cursor, and Gemini CLI previously received
  no always-on harness routing.
- Ideation Backlog (I-01…I-06) in `ROADMAP.md`: six documentation-only
  items distilled from an external intent-first-harness ideation note
  (evidence-classified intent contract, risk-adaptive discovery depth,
  read-only investigation mode, reclassification checkpoint,
  `patterns/refactoring/`, and a blocked repository-context contract).
  Disposition with rejected-items rationale:
  `docs/operational/reviews/harness-ideation-2026-07-15-status.md`.
- Test-first implementation program for the approved project-bootstrap policy:
  a master plan, six independently gated slice plans, a locked
  `python-build-standalone`/zipapp distribution decision, and a 31-criterion
  acceptance/evidence matrix. This is an implementation plan, not a claim that
  the planned subsystem exists yet.
- Approved design specification for the planned project-bootstrap and
  deterministic-policy subsystem: first-use discovery, a modular committed
  profile, a Python-first plugin contract, documentation/changelog requirements,
  layered Git/CI/completion gates, and protected policy reductions. This is a
  design milestone, not a claim that the subsystem is implemented.
- `harness-link.sh enforce-profile` gates Python, Go, and JS/TS projects.
  JS/TS covers Node's built-in `node --test` and Vitest
  (`coverage-summary.json`); Go uses `go test -coverprofile` and
  `go tool cover`. Jest/Mocha and unrecognized project types get an
  honest "not implemented" and exit 0 — or fail under the new `--strict`
  flag, so CI
  can require full coverage of the projects it gates.
- `harness-link.sh generate-clients <project> [--client …]` — runs the
  client-adapter generators into a consumer project in one command
  (AGENTS.md, GEMINI.md, Copilot, Cursor, Kilo) instead of the
  per-generator manual steps (P1-01 first increment).
- `tools/verify-skill-symlinks.sh` — verifies `.agents/skills/` stays 1:1
  with `.claude/skills/`, so a missing/broken symlink can't silently hide
  a skill from Agent-Skills-standard tools. Wired into `check.sh` + CI.
- `languages/rust/CONVENTIONS.md` (Rust guide, plus generated
  `rust.instructions.md`) and `patterns/accessibility/README.md` (a
  WCAG 2.2 / ARIA baseline).
- `docs/STATUS.md` and `docs/KNOWN_LIMITATIONS.md` — single current-state
  and open-gaps entry points.
- `tools/eval/.env.sample`, a documented instruction-quality (P2-03) eval
  plan, and `docs/operational/planning/DOGFOODING.md` (dogfood plan +
  tracking template).
- `AGENTHARNESS_SUBMODULE_REMOTE` override and `tools/check.sh --offline`
  for hermetic, network-free test runs (P1-05); lifecycle-transition
  tests (P1-06).
- Expanded worktree guidance (parallel-agent workflow, shared-hooks
  caveat) in the `branching` skill + `BRANCHING_STRATEGY.md`.
- Agent workflow: reviewers' comments must now be answered on the PR
  thread with an assessment + action taken, not only in a commit message
  or status file.

### Changed
- `enforce-profile` documentation corrected across `CODING_GUIDELINES.md`,
  `patterns/profiles/README.md`, `STATUS.md`, and the compatibility
  matrix to reflect the Go/Vitest/`--strict` reality.

### Fixed
- Four profile/workflow documentation contradictions (P1-03) and six
  stale `docs/CLIENT_COMPATIBILITY.md` cells that marked built adapters
  (Gemini/Copilot/Cursor/Kilo) as not existing yet.
- `--mode submodule`/`--mode npm` installed skill symlinks as absolute
  paths, which broke the moment the whole project (submodule and all)
  was moved or cloned to a different absolute path; now relative, so
  they survive a move.
- `cmd_update`/`cmd_audit`/`cmd_status` for `--mode submodule`/`--mode
  npm` trusted a stale absolute source path recorded at install time
  and hard-failed with "recorded source path no longer exists" after a
  project move, even though the source was still right there under the
  new location; now recomputed from the current target.

## [0.2.0] - 2026-07-13

### Added
- npm as a distribution channel: `package.json`, `bin/cli.js` (CLI shim
  execing `harness-link.sh`), and `.github/workflows/release.yml` (runs
  `npm publish` on a `v*` tag push) — built and tested end-to-end
  (`npm pack` → unpack → run) via CI's `npm-package` job, including a
  prepack/postpack symlink-materialization step so npm tarballs (which
  don't preserve symlinks) still ship the `agentic-loops` skill's bundled
  `agent_loop.py` correctly. Not yet actually published — no npm
  account/org or `NPM_TOKEN` secret exists (see `docs/DECISIONS.md`).
- A deterministic eval suite (`tools/eval/`) — task/scoring/orchestration
  infrastructure proving the harness *can* be measured against real
  tasks, with a free, fully-tested fake standing in for live agent
  invocation (`invoke_agent_via_api()` intentionally raises
  `NotImplementedError`; no eval results exist yet — see
  `docs/DECISIONS.md`).
- An `AGENTS.md` adapter for Codex, generated from `CLAUDE.md` +
  `.claude/skills/` by `tools/generate-agents-md.sh` (not hand-written,
  so it can't drift) — CI drift-checks it but it has not been verified
  against a real Codex CLI session; documented as best-effort only.
- An opt-in publish-authority flag (`.agentharness-publish-mode`,
  gitignored, per-operator): the harness's default agent behavior is now
  verify-and-stage-only — commit locally, then stop and ask before
  pushing, opening a PR, or auto-implementing a recommendation. Full
  publish authority requires the flag file or explicit per-task
  instruction. See `CLAUDE.md`'s "Agent Workflow Completion" and
  `docs/INTEGRATION.md`'s "Publish Authority" section.
- `harness-link.sh enforce-profile <project>`: makes
  `.agentharness-profile` do something mechanical instead of being a
  lookup table nothing reads — for a detected Python project, gates on
  the selected tier for real (`pytest --cov-fail-under` at that tier's
  floor; skips entirely where `tests.required` is false). Other project
  types get a clear "not implemented yet" rather than a false pass.
  Invoked explicitly (same posture as `audit`/`doctor`), not wired into
  `pre-push` automatically.
- `harness-link.sh audit --json` now also reports whether the target's
  publish-authority flag is active, its selected profile, and whether
  the recorded harness checkout's own validation commands
  (`tools/check.sh`, `verify-content-quality.py`, ...) still exist —
  catching a doc that claims a script exists after it's been renamed or
  deleted upstream.
- Duplicate-policy detection in CI: `check_duplicate_policy_numbers()` in
  `tools/verify-content-quality.py` flags a numeric mandate (currently
  the test-coverage percentage) restated with a genuinely *different*
  number outside its source of truth, via a small, explicit, extensible
  registry rather than general-purpose duplicate-content detection —
  deliberately doesn't flag every same-number restatement, only real
  conflicts, after two more naive designs produced real false positives
  against this repo's own content during development.
- `MANIFEST.md` is now generated from a structured `manifest.yaml` source
  by `tools/generate-manifest.py` (mirroring the `AGENTS.md` generator
  pattern, including a CI drift-check) instead of hand-maintained prose —
  `tools/verify-manifest.sh` still validates the rendered file against
  the filesystem on top of that.
- Snippet-syntax validation extended from Python-only to bash and console
  blocks: `check_bash_snippets()` (docs/INTEGRATION.md,
  `COVERAGE_REQUIREMENTS.md`'s bc-based coverage comparison) and
  `check_console_snippets()` (docs/DEMO.md's `$`-prefixed command
  lines), both via `bash -n` syntax-only checks — same small-allowlist
  principle as the Python check, not an auto-classifier.
- `docs/DEMO.md` — a 5-minute scripted walkthrough with real,
  hand-verified commands and output; `docs/DECISIONS.md` — a compact,
  retroactive architecture-decision log.
- `CLAUDE.md` mandates for agent workflow completion (verify and commit
  locally, always — full publish authority per the opt-in flag above) and
  recommendation assessment (implement scoped low-risk fixes directly;
  get confirmation before a batch that amounts to a roadmap; escalate
  anything high-risk).
- Rigor-tier profiles as selectable YAML (`patterns/profiles/`), not
  just prose — Prototype/Internal/Production now have a machine-readable
  config, not only a table in `CODING_GUIDELINES.md`.
- A lifecycle CLI for `harness-link.sh`: `status`, `doctor`, `audit`,
  `update`, `uninstall` alongside the original `init`, so a consuming
  project can inspect and manage its integration instead of only ever
  running the initial install once.
- Consumer fixtures for all three install modes (link/copy/submodule)
  across Python, TypeScript, and Go sample projects, exercised by CI's
  `fixture-matrix` job — previously only one symlink-mode sample existed.
- Pinned dev/CI toolchain (`requirements-dev.txt`), a single local
  verification entrypoint (`tools/check.sh`), and a `content-quality` CI
  job (`git diff --check`, `markdownlint-cli2`, YAML/frontmatter/
  embedded-snippet validation via `tools/verify-content-quality.py`).
- `error-handling` and `agentic-loops` pattern guides, each with a real,
  tested reference implementation (not just prose) and matching Claude
  Code skills; `audit-review-followup` skill for re-scoring a past
  review against current repo state.
- `languages/typescript/`, `languages/go/`, and `frameworks/react/`
  (split out of the TypeScript guide) convention guides.
- A product contract in the README (target users, supported clients/
  platforms, what gets installed, advisory vs. enforced, non-goals).
- `docs/RELEASING.md` — versioning policy, release checklist, and a
  tested pin/rollback/upgrade demonstration
  (`tools/tests/harness-lifecycle.bats`).

### Changed
- `harness-link.sh` rewritten around a single lifecycle CLI shape
  (`init`/`plan`/`status`/`doctor`/`audit`/`update`/`uninstall`) recording
  state in `.agentharness-state.json`, instead of a one-shot install
  script with no memory of what it did.
- Rewrote `patterns/testing/README.md` from a ~464-line near-duplicate of
  the other testing docs into a short index; rescoped `TDD.md`,
  `COVERAGE_REQUIREMENTS.md`, `COMPLETION_CHECKLIST.md`, and
  `PLAYWRIGHT_UI_TESTING.md`'s "80% mandatory, no exceptions" language to
  the Production tier specifically, reconciling it with the rigor-tier
  table it previously contradicted.
- `docs/INTEGRATION.md` and `README.md` rewritten against what actually
  exists and what actually runs — tree diagram regenerated from
  `git ls-files`, HTTPS-primary clone instructions, per-skill symlink
  loops (not a stale 3-skill hardcoded list) verified in a clean scratch
  directory for every method (symlink/copy/submodule).
- Trimmed the language convention guides, logging docs, testing docs,
  `error-handling/README.md`, and `BRANCHING_STRATEGY.md` down to
  repo-specific decisions — cut generic, ecosystem-standard content that
  didn't need to live in this harness at all (an encyclopedia is a
  maintenance liability; a pointer to the real docs isn't).

### Fixed
- `harness-link.sh --mode submodule` recorded `source.path` as the dev
  checkout's own path instead of the submodule inside the consuming
  project, causing `update`/`audit` to report phantom drift; submodule
  add now pins to harness's exact commit instead of the remote's mutable
  default branch.
- CI supply-chain: pinned `bats-core` to its dereferenced commit SHA
  (was pointing at an annotated tag object's own SHA, which isn't a
  commit `actions/checkout` can use), pinned `markdownlint-cli2`, added a
  `--yes` non-interactive flag where the matrix job needed it.
- `docs/INTEGRATION.md`'s copy-mode example used `cp -r` (produces a
  dangling symlink for `agentic-loops/agent_loop.py`, since it copies the
  symlink instead of the file it resolves to) and a single-quoted
  heredoc that silently discarded its own `$(git rev-parse ...)`
  expansion — both reproduced, in docs, bugs already fixed in the real
  tool; fixed to `cp -rL` and an unquoted heredoc with a precomputed
  variable.
- Assorted shellcheck (SC2115, SC2034), whitespace, and markdown-lint
  violations caught only once CI actually gained the checks to catch
  them (`content-quality` job, local `shellcheck`/`git diff --check`).

## [0.1.0] - 2026-07-11

### Fixed
- `prevent-trunk-commit` hook: blocked the first commit of every fresh
  repo due to an unborn-branch bug (`git rev-parse --abbrev-ref HEAD`
  fails before any commit exists); switched to `git symbolic-ref`. Added
  `release/*` prefix matching to match the documented branch convention.
  Covered by `.github/hooks/tests/prevent-trunk-commit.bats`.
- Removed a dozen broken or non-functional shell snippets across
  `docs/`, `.github/BRANCHING_STRATEGY.md`, and `patterns/testing/` (bad
  symlink targets, wrong BFG syntax, a Go coverage check that crashed on
  floats, an invalid Python refactor example, duplicated `.gitignore`
  templates with contradictory advice).
- `.github/.gitignore.template` was ignoring `go.sum`, `lib/`, `vendor/`,
  and version-pin files (`.nvmrc`, `.python-version`, …) that should be
  committed for reproducible builds.
- Reconciled three conflicting coverage-tier tables (one had an
  off-by-one split at 79% instead of 75%) into a single source of truth
  in `COVERAGE_REQUIREMENTS.md`.
- Reconciled a genuine contradiction between "one comprehensive
  assertion" and "one assertion per test" testing guidance.

### Added
- `MANIFEST.md` — accurate index of every real asset in the repo.
- `ROADMAP.md` — aspirational directory structure moved here, clearly
  labeled as not-yet-built (previously presented as current state).
- `LICENSE` (MIT).
- `SECURITY.md` — secrets-in-history procedure.
- Rigor tiers in `CODING_GUIDELINES.md` (Prototype / Internal Tool /
  Production Service) — reconciles the doc's minimalism principles with
  its 80%-coverage/Playwright/OTEL mandates, which previously applied
  uniformly with no scale-down path.
- `.claude/skills/{committing,branching,python-conventions}/` — the
  first real Claude Code skills in the repo, loaded on demand instead of
  via manual copy/symlink.
- `tools/setup/harness-link.sh` — one-command project integration.
- `.github/workflows/ci.yml` — shellcheck, hook tests (bats), markdown
  link check. The repo mandates CI for consuming projects but had none
  of its own until now.
- Concrete mechanisms for two previously-unenforceable mandates:
  screenshot-approval (`PLAYWRIGHT_UI_TESTING.md`) and
  logging-verification (`LOGGING_STANDARDS.md`) now specify what to
  actually do and record, not just "must be reviewed."

### Changed
- Repository renamed `awesome-harness` → `agentharness` (the `awesome-*`
  prefix conventionally signals a curated link list on GitHub; this is a
  toolkit).
- `CLAUDE.md` slimmed from ~450 lines of prose to a short router — it's
  loaded into every session of every consuming project, so its size is a
  per-task cost.
- Standardized on `.env.sample` over `.env.example` repository-wide.
- Branch protection enabled on `main` (PRs required; admin bypass left
  open).

### Removed
- `.github/accessibility.instructions.md` — was entirely VS Code
  source-internal (`AccessibleContentProvider`,
  `CONTEXT_ACCESSIBILITY_MODE_ENABLED`, a specific VS Code PR number)
  despite claiming general applicability. Noted as a real gap in
  `ROADMAP.md` rather than silently dropped.
- Fabricated before/after statistics ("~95% of bugs prevented," "0
  failed deployments") from four docs.
- Hand-written "Last Updated" date lines (18 files) — git already tracks
  this, and the hand-maintained dates had all drifted to the same value
  regardless of actual last edit.
