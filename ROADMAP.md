# Roadmap

This file holds the **target** shape of the repo — components that are
planned but don't exist yet. Nothing in this file should be treated as
available. If you're an agent reading this to decide whether to symlink,
copy, or reference something: **check the actual directory first.** This
file describes intent, not inventory.

See [MANIFEST.md](MANIFEST.md) for what actually exists today.

## Planned Components

### `.claude/agents/`
Custom agent definitions for specialized tasks (code explorers, architects,
reviewers, debuggers). Not started.

### `.claude/hooks/`
Claude Code event hooks (as distinct from git hooks in `.github/hooks/`).
Not started.

### `.codex/`
Configuration for OpenAI Codex CLI, mirroring what `.claude/` does for
Claude Code. Not started. (Earlier drafts of this repo mislabeled this as
"Anthropic Codex" — Codex is an OpenAI product; any future `.codex/`
content should not imply Anthropic affiliation.)

### `frameworks/{react,vue,angular,django,express,go}/`
Framework-specific config templates, patterns, and examples. Only the
category README exists today; no framework subdirectories have been built.

### `languages/{typescript,go,rust,...}/`
Additional language convention guides, following the shape of the existing
`languages/python/`. Only Python exists today.

### `patterns/{agentic-loops,error-handling,api-design,accessibility}/`
Additional pattern categories, following the shape of the existing
`patterns/testing/` and `patterns/logging/`. Only those two exist today.

A genuine cross-framework accessibility pattern doc is a real gap — an
earlier draft (`accessibility.instructions.md`) was removed because it
was entirely VS Code source-internal (`AccessibleContentProvider`,
`CONTEXT_ACCESSIBILITY_MODE_ENABLED`, references to specific VS Code
PRs) despite claiming general applicability. A real version needs to be
written from ARIA/WCAG fundamentals, not adapted from one codebase's
internal APIs.

### `tools/{lint,build,deploy}/`
Standalone utility scripts. Only the category README exists today; no
tools have been built. The one real script in the repo is
`.github/hooks/prevent-trunk-commit` and `tools/setup/harness-link.sh`.

### `.github/workflows/`
Reusable CI workflows for consuming projects. Not started. This repo's own
CI (markdown link check, shellcheck, hook tests) is implemented in `ci.yml`.

### `dependabot.yml`, `CODEOWNERS`
Implemented: `.github/dependabot.yml` (Go modules + GitHub Actions updates)
and `.github/CODEOWNERS` (review routing for framework/GitHub config areas).

### Claude Code Skills (`.claude/skills/`)
Implemented: `committing`, `branching`, `python-conventions` with full
frontmatter, loading on demand. These are the initial high-value skills; more
language/pattern skills can follow the same template.

## Explicitly Deferred / Needs a Decision

- ~~Sample integration project~~ — **IMPLEMENTED** (item 23). Symlink
  method (`examples/sample-project/`) is validated by CI's
  `sample-project-integration` job, which runs `harness-link.sh --with-hook`
  against a scratch copy and checks the result — not hand-verified. Copy and
  submodule methods are documented in the sample's README but not
  independently CI-checked; a smaller follow-up if that gap matters later.

- ~~Logging config loader~~ — **IMPLEMENTED** (item 12). Python utility
  `config_loader.py` with tests for loading YAML configs with `${VAR:-default}`
  environment variable interpolation. Documentation integrated into
  `LOGGING_STANDARDS.md`.

- **Profiles + precedence system** (`gpt-5.6-review.md` P1-02) — `prototype`
  / `internal` / `production` profiles that *select* policies instead of
  the current single set of universal mandates qualified only by prose
  ("Rigor Tiers"). Real feature work, not a fix — needs its own design
  pass on what a profile actually gates (coverage %? logging backends?
  screenshot requirements?) before implementation.

- **Lifecycle CLI for `harness-link.sh`** (P1-04) — `init`/`plan --dry-run`/
  `status`/`audit`/`update`/`uninstall`, with a state file recording what
  was installed. The current script is one-shot install-only; this is a
  rewrite, not a patch.

- **Consumer fixtures beyond the symlink path** (P1-05) — CI currently
  proves `harness-link.sh --with-hook` (symlink mode) end-to-end via
  `examples/sample-project`. The copy and submodule integration paths
  documented in `docs/INTEGRATION.md` are not independently exercised in
  CI.

- **Technical edit pass on TypeScript/Go guides** (P1-09) — `gpt-5.6-review.md`'s
  "Content correctness" section lists concrete defects: `languages/typescript/CONVENTIONS.md`
  calls `_private` fields "deprecated" (not a real TS deprecation), uses
  `Map<string, any>` while the same policy says avoid `any`, and claims a
  small regex is RFC 5322-compliant (it isn't). `languages/go/CONVENTIONS.md`
  flags an already-camelCase identifier as wrong, uses deprecated
  `ioutil.ReadFile` over `os.ReadFile`, and defines methods on
  `*UserRepository` after presenting `UserRepository` as an interface
  (doesn't compile). Not fixed in this pass — see
  `docs/operational/reviews/gpt-5.6-review-status.md` for why.

- **Full agentic-loop safety framework** (P0-07's full scope beyond the
  crash-bug fixes already shipped) — JSON Schema validation of tool
  arguments against a declared schema, approval boundaries, sandboxing,
  time/token/cost budgets, cancellation, idempotency, prompt-injection
  handling, and persistence/resume. The crash bugs (missing imports,
  uninitialized state, task never reaching the model, no call-id
  correlation) are fixed; the safety framework is a system to design, not
  a bug to patch.

- **CI supply-chain hardening** (P1-07) — pin GitHub Actions and the Bats
  install to reviewed revisions instead of a mutable default branch
  installed with `sudo`; add `permissions: contents: read` to the
  workflow; add step timeouts.
