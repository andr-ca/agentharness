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
