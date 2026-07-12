# agentharness

A centralized repository for coding-agent instructions, conventions, and
git/testing/logging guidelines, reused across projects instead of
duplicated in each one.

## Purpose

Every project accumulates its own CLAUDE.md, commit conventions, and CI
rituals; drift between projects is real and costly. This repo is the
single source of truth for that shared context — read once here, referenced
(not copy-pasted-and-forgotten) from every consuming project.

**Status:** early. See [MANIFEST.md](MANIFEST.md) for what actually exists
today and [ROADMAP.md](ROADMAP.md) for what's planned but not built. Don't
trust a directory tree in prose — trust the manifest.

## Product Contract

**Target users:** teams or individuals running multiple projects with a
coding agent, who want git/testing/logging/language conventions written
once and referenced everywhere instead of re-authored (and drifting) per
project.

**Supported clients:** Claude-first. The skills under `.claude/skills/`
and the `CLAUDE.md` router are built for and tested with Claude Code. The
language/pattern guides under `languages/` and `patterns/` are plain
Markdown and usable by any agent or human that can read a file, but no
other agent's skill/tool-loading mechanism has been tested against this
repo yet — don't assume Cursor, Copilot, or another harness picks up
`.claude/skills/` the same way Claude Code does.

**Supported platforms:** Linux and macOS (Bash scripts, POSIX shell
conditionals, `bats-core` for shell tests). Windows is untested; WSL
should work but hasn't been verified.

**What gets installed** by `tools/setup/harness-link.sh init` (a
lifecycle CLI — also exposes `plan`/`status`/`doctor`/`audit`/`update`/
`uninstall`; see [docs/INTEGRATION.md](docs/INTEGRATION.md)) into a
consuming project:
- Selected (or all) `.claude/skills/<name>` directories, symlinked
  (`--mode link`, default), physically copied (`--mode copy`), or
  symlinked from a git submodule this creates at `.agentharness`
  (`--mode submodule` — the one mode that does reach the network, to add
  that submodule).
- A merge of `.github/.gitignore.template` into the project's `.gitignore`
  (additive — never overwrites existing entries).
- With `--with-hook`: `core.hooksPath` pointed at this repo's
  `.github/hooks/` (refuses to overwrite an existing, different
  `core.hooksPath` unless `--force` is passed — see
  `tools/tests/harness-link.bats`).
- A `.agentharness-state.json` recording mode, source revision, and
  installed skills, so `status`/`doctor`/`update`/`uninstall` know what
  they're working with.

Nothing else is installed. No telemetry, no background processes; no
network calls except the one submodule-mode clone above, which only
happens if you asked for that mode.

**Advisory vs. enforced:**
- *Advisory* (a convention the agent is expected to follow, not something
  that blocks anything): `CLAUDE.md`, the skill files under
  `.claude/skills/`, and every guide under `languages/` and `patterns/`.
  An agent (or a human) can ignore these; nothing stops them mechanically.
- *Enforced* (a script that actually blocks an action): the
  `prevent-trunk-commit` pre-commit hook (blocks direct commits to trunk
  branches) and the `pre-push` hook (blocks a push below 80% test
  coverage or a failing test suite) — both only apply once a project
  opts in via `--with-hook`, and both only test *this* repo's own
  suites when pushing to *this* repo (see `.github/hooks/pre-push`'s
  own comments for how it detects and no-ops for a borrowing consumer).

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

```
agentharness/
├── README.md                    # This file
├── CLAUDE.md                    # Agent-facing router + mandatory rules
├── MANIFEST.md                  # Index of every real asset
├── ROADMAP.md                   # What's planned but not built yet
├── CHANGELOG.md                 # Release history
├── SECURITY.md                  # Secrets-in-history procedure
├── .github/
│   ├── BRANCHING_STRATEGY.md
│   ├── COMMITTING_GUIDELINES.md
│   ├── CODING_GUIDELINES.md
│   ├── pull_request_template.md
│   ├── .gitignore.template
│   ├── workflows/               # CI for this repo
│   └── hooks/
│       └── prevent-trunk-commit
├── .claude/
│   └── skills/                  # committing, branching, python-conventions
├── languages/
│   └── python/                  # CONVENTIONS.md, COPILOT_INSTRUCTIONS.md
├── patterns/
│   ├── testing/                 # TDD, coverage, Playwright, completion checklist
│   └── logging/                 # logging standards + example config
├── tools/
│   └── setup/
│       └── harness-link.sh      # One-command project integration
└── docs/
    ├── ARCHITECTURE.md
    └── INTEGRATION.md
```

Everything else you might expect (frameworks/, more languages, more
pattern categories, `.claude/agents/`, `.codex/`) is intentionally not
here yet — see [ROADMAP.md](ROADMAP.md).

## Quick Start

```bash
git clone git@github.com:andr-ca/agentharness.git ~/agentharness
```

Integrate into a project with the setup script (installs skills, copies
the gitignore template, and — if you opt in — the branch-protection hook):

```bash
~/agentharness/tools/setup/harness-link.sh /path/to/your-project
```

Or by hand — see [docs/INTEGRATION.md](docs/INTEGRATION.md) for the
symlink/copy/submodule tradeoffs.

## Contributing

1. Check [MANIFEST.md](MANIFEST.md) — don't duplicate an existing asset.
2. New content gets a real usage example, not just a description.
3. Skills need frontmatter (see any file in `.claude/skills/` for the
   shape).
4. Add an entry to MANIFEST.md.
5. Every change goes through a feature branch and PR — see
   `.github/BRANCHING_STRATEGY.md`. Branch protection on `main` enforces
   this for everyone except repo admins.

## License

See [LICENSE](LICENSE).
