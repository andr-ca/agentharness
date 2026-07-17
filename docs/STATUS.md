# Current Status

A single, maintained snapshot of **what actually works in this repo
today** — so you don't have to reconstruct it from
[MANIFEST.md](../MANIFEST.md) (asset inventory),
[ROADMAP.md](../ROADMAP.md) (what's *not* built), and the dated review
notes under [docs/operational/reviews/](./operational/reviews/) all at
once. Open gaps live in one companion file:
[KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

This page is a **summary that links to the authoritative source for each
row** — it deliberately does not restate detail those files own, so it
can't drift into a competing third version (the exact failure mode
[ROADMAP.md](../ROADMAP.md)'s P1-03/P1-10 exist to prevent). If a fact
here disagrees with the linked source, the linked source wins and this
line is the bug.

- **Maintained by hand** — update it in the same PR that changes what it
  describes.
- **Last verified against the tree:** 2026-07-17 (commit `af36f2c`).
- **Standing caveat:** everything except Claude Code is implemented
  against each tool's *published* behavior, **not** dogfooded against a
  live session — see
  [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s intro and
  [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

## Release

- **Current version:** `v0.2.1` (npm `package.json`; `pyproject.toml` at 0.1.1 — Python core is experimental/unreleased). Published to
  npm as `agentharness-toolkit`. See
  [RELEASING.md](./RELEASING.md) and [DECISIONS.md](./DECISIONS.md).

## Client support (built)

Per-tool loading behavior and the full matrix (including the ⚠️/❌ rows)
live in [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md); this is
just what's generated and committed here today.

| Tool | Always-on instructions | On-demand skills |
|---|---|---|
| Claude Code | `CLAUDE.md` (hand-authored source) | `.claude/skills/` (source) |
| Codex CLI | `AGENTS.md` | `.agents/skills/` |
| Gemini CLI / Antigravity | `GEMINI.md` | `.agents/skills/` |
| GitHub Copilot | `.github/copilot-instructions.md` + `.github/instructions/*` | `.agents/skills/` |
| Cursor | `.cursor/rules/*.mdc` | `.cursor/rules/<skill>.mdc` |
| Kilo Code | `.kilo/rules/agentharness.md` | `.agents/skills/` |
| OpenCode / Zed | `AGENTS.md` (their own convention) | `.agents/skills/` |

Generate these into a consumer project in one command with
`harness-link.sh generate-clients <project> --client all` (P1-01 first
increment).

Every generated file is drift-checked in CI against its `CLAUDE.md` /
`CONVENTIONS.md` / skill source. **One custom sub-agent**
(`coding-guidelines-reviewer`) and its per-tool ports are tracked
separately — see [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s
custom-agent table.

## Install modes (built)

`link`, `copy`, `submodule`, and `npm` — all installable via
`tools/setup/harness-link.sh` (or `npx agentharness-toolkit`), with
`init`/`plan`/`status`/`doctor`/`audit`/`enforce-profile`/`update`/
`uninstall` lifecycle commands and state in
`<project>/.agentharness-state.json`. See [INTEGRATION.md](./INTEGRATION.md).

## Content (built)

| Area | Built today | Source of truth |
|---|---|---|
| Languages | Python, TypeScript, Go, Rust | [languages/](../languages/) |
| Frameworks | React | [frameworks/react/](../frameworks/react/) |
| Patterns | testing, logging, agentic-loops, error-handling, profiles, accessibility, api-design, clean-architecture, dependency-injection, design-patterns, file-placement-policy, multi-agent-coordination, mutation-testing, solid-principles | [patterns/](../patterns/) |
| Skills | 32 (accessibility, agentic-loops, api-design, audit-review-followup, branching, clean-architecture, code-review, code-review-api, code-review-db, code-review-ui, committing, database-conventions, dependency-audit, dependency-injection, design-patterns, docker-conventions, error-handling, file-placement-policy, go-conventions, logging, multi-agent-coordination, mutation-testing, performance-profiling, planning-with-files, port-agent-config, python-conventions, react-best-practices, requirements-clarification, security-review, solid-principles, testing, typescript-conventions) | [.claude/skills/](../.claude/skills/) |

## Enforcement (built)

- **Trunk commit prevention** — `prevent-trunk-commit` pre-commit hook blocks
  direct commits to trunk branches; installed when a project opts in via
  `harness-link.sh --with-hook`.
- **File placement** — `tools/check-file-placement.sh` pre-commit check blocks
  commits that add files to paths listed in `.agentharness-guarded-paths.json`
  without a recorded approval in `.agentharness-allowed-additions.txt`.
- **Agent completion gate** — `tools/check-completion.sh` (wired as a Stop hook
  for Claude Code via `.claude/settings.json` and GitHub Copilot via
  `.github/hooks/completion-gate.json`) verifies lint, types, tests, coverage,
  and content quality; an agent can't end its session until the gate exits 0.
- **Multi-agent mutex** — `tools/agent-lock.sh check-branch` (called in the
  `pre-push` hook) blocks pushes to a branch whose lock another live session
  holds. A Claude Code `PreToolUse` guard (`.github/hooks/claude-push-lock-guard.sh`)
  blocks `git push` tool calls even before the pre-push hook fires. A repo-wide
  GitHub ruleset (`no-force-push-any-branch`, no bypass actors) prevents
  force-pushes on every branch.
- **Profile enforcement** (`harness-link.sh enforce-profile`) gates for
  real on **Python** (`pytest`), **Go** (`go test` + `go tool cover`),
  and **`node --test`/Vitest JS/TS** projects at the selected tier's
  coverage floor; Jest/Mocha and unrecognized project types are advisory
  (exit 0, or fail under `--strict`). Not yet wired into the pre-push
  hook. Source of truth: [patterns/profiles/README.md](../patterns/profiles/README.md).
- **Publish authority** defaults to verify-and-stage; push/PR requires
  the opt-in `.agentharness-publish-mode` flag. See
  [DECISIONS.md](./DECISIONS.md).

## Verification (built)

`tools/check.sh` runs everything CI runs locally: shellcheck, bats
suites, ruff, mypy, pytest with coverage gates, `MANIFEST.md`
verification, skill-symlink integrity, and the content-quality checks
(markdownlint, YAML/frontmatter/snippet validation, `MANIFEST`/`AGENTS`
sync, duplicate-policy detection). CI mirrors these as separate jobs
plus a sample-project integration matrix and an npm pack/unpack drive.
