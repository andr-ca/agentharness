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

### `patterns/{agentic-loops,error-handling,api-design}/`
Additional pattern categories, following the shape of the existing
`patterns/testing/` and `patterns/logging/`. Only those two exist today.

### `tools/{lint,build,deploy}/`
Standalone utility scripts. Only the category README exists today; no
tools have been built. The one real script in the repo is
`.github/hooks/prevent-trunk-commit` and `tools/setup/harness-link.sh`.

### `.github/workflows/`
Reusable CI workflows for consuming projects. Not started. This repo's own
CI (markdown link check, shellcheck, hook tests) lives here once added —
see `docs/operational/` for tracking.

### `dependabot.yml`, `CODEOWNERS`
Referenced by `.github/README.md` in earlier drafts as if present. Not
created yet.

### Claude Code Skills (`.claude/skills/`)
Converting the strongest guideline docs (committing, branching, Python
conventions) into on-demand skills with proper frontmatter, so agents load
them only when relevant instead of via manual copy/symlink. This is the
highest-leverage item on this roadmap — see `MANIFEST.md` for current
skill status.

## Explicitly Deferred / Needs a Decision

- **Sample integration project** — a tiny project that consumes this repo
  via each integration method (symlink/copy/submodule), kept green by CI,
  so every command in `docs/INTEGRATION.md` is validated automatically
  rather than hand-verified. Meaningful effort; not started.
- **Version tagging (`v0.1.0`, CHANGELOG-driven releases)** — deferred
  until the P0/P1 accuracy and consistency fixes have landed, so the first
  tagged version isn't tagging known-broken content.
