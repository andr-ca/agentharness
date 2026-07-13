# agentharness

[![CI](https://github.com/andr-ca/agentharness/actions/workflows/ci.yml/badge.svg)](https://github.com/andr-ca/agentharness/actions/workflows/ci.yml)

Portable engineering policies for coding agents — git, testing, logging,
and language conventions written once and referenced everywhere, instead
of re-authored (and drifting) in every project's own `CLAUDE.md`.

## Purpose

Every project accumulates its own CLAUDE.md, commit conventions, and CI
rituals; drift between projects is real and costly. This repo is the
single source of truth for that shared context — read once here, referenced
(not copy-pasted-and-forgotten) from every consuming project.

**Status:** early. See [MANIFEST.md](MANIFEST.md) for what actually exists
today and [ROADMAP.md](ROADMAP.md) for what's planned but not built. Don't
trust a directory tree in prose — trust the manifest.

### Why not just CLAUDE.md?

A single project's `CLAUDE.md` works fine — until there's a second
project, and its `CLAUDE.md` quietly diverges: a different coverage bar,
a branch-naming rule that contradicts the first repo's, a logging
convention nobody remembers deciding. Multiply by N projects and the
conventions aren't really policies anymore, just N independent guesses
that happen to overlap. agentharness is the fix for that specific
problem: one `CLAUDE.md` router plus a set of skills and convention docs
that every project's own (short) `CLAUDE.md` *references* — see
[docs/INTEGRATION.md](docs/INTEGRATION.md). You still write a
project-specific `CLAUDE.md`; it just stops being where the shared rules
live.

**Agent publish authority is opt-in, not default.** `CLAUDE.md` has an
agent verify and stage work locally, then stop and ask before pushing,
opening a PR, or auto-implementing a recommendation — full authority to
do those requires a local `.agentharness-publish-mode` flag file (never
committed) or explicit per-task instruction. See
[docs/INTEGRATION.md](docs/INTEGRATION.md)'s "Publish Authority" section.

**Non-goals** — this project deliberately does not:
- Orchestrate or run agents itself (no agent loop, scheduler, or runtime
  lives here beyond the one tested reference example in
  `patterns/agentic-loops/`).
- Replace language-specific linters, formatters, or CI systems — it
  documents conventions for using them, not a competing implementation.
- Guarantee behavior on any agent harness other than Claude Code today
  (see "Supported clients" above).
- Auto-update a consuming project. The symlink mode means a project
  picks up changes when this repo's checkout changes, but nothing here
  pushes updates or reaches into a consumer uninvited.

## What's here today

This tree lists tracked files only (a fresh clone won't have empty
placeholder directories) — see [MANIFEST.md](MANIFEST.md) for the full,
current inventory with a one-line purpose per file; treat this as an
orientation map, not the source of truth.

```
agentharness/
├── README.md                    # This file
├── CLAUDE.md                    # Agent-facing router + mandatory rules
├── AGENTS.md                    # Codex adapter, generated from CLAUDE.md + skills (untested)
├── MANIFEST.md                  # Index of every real asset
├── ROADMAP.md                   # What's planned but not built yet
├── CHANGELOG.md                 # Release history
├── SECURITY.md                  # Secrets-in-history + instruction-attack-surface procedure
├── CONTRIBUTING.md              # Contribution workflow
├── CODE_OF_CONDUCT.md           # Contributor Covenant
├── requirements-dev.txt         # Pinned dev/CI toolchain
├── .markdownlint-cli2.yaml      # Markdown lint rules for CI
├── .github/
│   ├── BRANCHING_STRATEGY.md
│   ├── COMMITTING_GUIDELINES.md
│   ├── CODING_GUIDELINES.md
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/          # bug_report.md, feature_request.md
│   ├── .gitignore.template
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── workflows/               # ci.yml, link-check-scheduled.yml
│   └── hooks/                   # prevent-trunk-commit, pre-push (+ tests)
├── .claude/
│   └── skills/                  # committing, branching, python-conventions,
│                                 # error-handling, agentic-loops,
│                                 # audit-review-followup
├── languages/
│   ├── python/                  # CONVENTIONS.md, COPILOT_INSTRUCTIONS.md
│   ├── typescript/              # CONVENTIONS.md
│   └── go/                      # CONVENTIONS.md
├── frameworks/
│   └── react/                   # CONVENTIONS.md (add-on to the TS guide)
├── patterns/
│   ├── testing/                 # TDD, coverage, Playwright, completion checklist
│   ├── logging/                 # logging standards + example config + loader
│   ├── error-handling/          # retry, circuit-breaker, structured logging
│   ├── agentic-loops/           # tested agent-loop reference implementation
│   └── profiles/                # rigor-tier profiles (prototype/internal/production)
├── examples/                    # sample-project + python/typescript/go fixtures,
│                                 # each verified in CI across every install mode
├── tools/
│   ├── setup/harness-link.sh    # Lifecycle CLI: init/plan/status/doctor/audit/update/uninstall
│   ├── check.sh                 # One local entrypoint for every CI check
│   ├── verify-manifest.sh       # This file's own accuracy check
│   ├── verify-content-quality.py
│   └── tests/                   # bats tests for harness-link.sh
└── docs/
    ├── ARCHITECTURE.md
    ├── INTEGRATION.md
    ├── RELEASING.md              # Versioning policy, release checklist, pin/upgrade/rollback
    └── operational/              # working notes, review history
```

Everything else you might expect (more `frameworks/`, more `languages/`,
`.claude/agents/`, `.codex/`) is intentionally not here yet — see
[ROADMAP.md](ROADMAP.md).

## Quick Start

**Prerequisites:** `git`, `bash`, `python3` (used to read/write the
lifecycle CLI's state file). See "Supported platforms" above.

```bash
git clone https://github.com/andr-ca/agentharness.git ~/agentharness
```

(Or `git@github.com:andr-ca/agentharness.git` if you have SSH access set
up and prefer it — HTTPS works with no additional setup, which is why
it's the default above.)

Integrate into a project with the setup script (installs skills, merges
the gitignore template, and — if you opt in via `--with-hook` — the
branch-protection + coverage hooks):

```bash
~/agentharness/tools/setup/harness-link.sh init /path/to/your-project
```

Preview what that would do without changing anything: add `--dry-run` (or
run `plan` instead of `init`). Verify afterward with
`~/agentharness/tools/setup/harness-link.sh doctor /path/to/your-project`.

Or by hand — see [docs/INTEGRATION.md](docs/INTEGRATION.md) for the
symlink/copy/submodule tradeoffs, troubleshooting, and update/uninstall.
See [docs/DEMO.md](docs/DEMO.md) for a 5-minute walkthrough with real
commands and real output — what `init` actually installs, and what the
enforced trunk-protection hook looks like when it fires.

**npm, as an alternative to `git clone`:** `npx agentharness init
/path/to/your-project` runs the same lifecycle CLI without a separate
clone step (still needs `bash`/`python3` on your machine). This packaging
exists and has been verified locally (`npm pack --dry-run`) but **has not
yet been published to npm** — see
[docs/RELEASING.md#npm-distribution](docs/RELEASING.md#npm-distribution)
for exactly what's missing. Until it's published, use the `git clone`
path above.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow (branching,
local verification, review routing). Short version: check
[MANIFEST.md](MANIFEST.md) before adding anything, run
`bash tools/check.sh` before opening a PR, and go through a feature
branch — never commit directly to `main`. This project follows the
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

See [LICENSE](LICENSE).
