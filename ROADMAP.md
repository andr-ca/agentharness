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

- ~~Sample integration project~~ — **IMPLEMENTED** (item 23, expanded
  under P1-05). `examples/sample-project/` (blank/generic) is validated
  by CI's `sample-project-integration` job against link mode +
  `--with-hook`. `examples/{python,typescript,go}-project/` (each with a
  realistic pre-existing `.gitignore`) are validated by the
  `fixture-matrix` job across all three install modes (link/copy/
  submodule) plus `doctor`/`status`/`update`/`uninstall` — not just
  install-and-check. Finding this gap live is what turned up the
  --mode copy bundled-resource-symlink bug fixed alongside P1-05.

- ~~Logging config loader~~ — **IMPLEMENTED** (item 12). Python utility
  `config_loader.py` with tests for loading YAML configs with `${VAR:-default}`
  environment variable interpolation. Documentation integrated into
  `LOGGING_STANDARDS.md`.

- **Profile-enforcement wiring in `.github/hooks/pre-push`.** Not started.
  `patterns/profiles/` defines `.agentharness-profile` (prototype/internal/
  production) as a lookup a project or agent can consult, but no script
  reads it yet. The hook currently only ever runs *this* repo's own
  hardcoded test suites and no-ops for a consumer's push, so there's
  nothing for a profile to gate there today. Wiring this up depends on
  the hook (or a successor lifecycle CLI) first learning to discover and
  run a *consumer's own* test suite — do both together, not the gate
  alone with nothing real to enforce.
