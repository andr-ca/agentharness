# Integration Guide – Using agentharness in Projects

Step-by-step guide for integrating components from agentharness into your
projects. Every command below is tested against what actually exists in
this repo today — see [MANIFEST.md](../MANIFEST.md) for the inventory.

## The Fast Path

```bash
~/agentharness/tools/setup/harness-link.sh init /path/to/your-project --mode link
```

This is `harness-link.sh`'s lifecycle CLI: `init` symlinks (or copies, or
adds a submodule and symlinks from it — see Method 1/2/3 below) skills,
merges `.github/.gitignore.template` into `.gitignore`, optionally
installs the trunk-protection + coverage hooks (`--with-hook`), and
records everything in `<project>/.agentharness-state.json` so the other
subcommands can act on it later:

| Subcommand | What it does |
|---|---|
| `init` | Install (see modes below). `--dry-run` (or the `plan` alias) shows what would happen without changing anything. |
| `status` | What's installed, from where, and whether the source has moved on since. |
| `doctor` | Validate the install is healthy (skills present, bundled resources resolve, hook configured); nonzero exit if not — usable as a CI check. |
| `audit` | Report drift: skills available upstream but not installed, installed skills no longer available, commits since your recorded revision. |
| `update` | Re-sync to the current harness state; shows a diff and asks for confirmation (`--yes` to skip it) before changing anything. |
| `uninstall` | Reverse everything `init` recorded — skills, gitignore block, hook, profile file, state file (and the submodule, in that mode). |

`harness-link.sh /path/to/your-project [options]` (no subcommand) still
works — it's sugar for `init` with those same options, kept for anything
that already calls it that way.

Everything below is the manual, step-by-step version of what `--mode`
does, useful for understanding what's actually happening or for
integrating a single component by hand instead of everything at once.

## Integration Methods

### Method 1: Symlinks (recommended for active development)

Keep your project in sync with harness updates automatically.

Automated: `harness-link.sh init ~/my-project --mode link` (the default —
`--mode` can be omitted).

Manual, what that does under the hood:

```bash
cd ~/my-project
mkdir -p .claude
ln -s ~/agentharness/.claude/skills .claude/skills
```

**Pros:** Always up-to-date. **Cons:** Requires the harness checked out
locally at that exact path; breaks if you move it.

⚠️ Never symlink into `~/.claude` (your global Claude Code config) — that
clobbers or fights with settings that aren't part of this harness.
Symlink into the *project's* `.claude/`, not your home directory.

### Method 2: Copy (for release stability)

Lock to a specific snapshot of harness components — no drift, no
dependency on the harness being checked out locally.

Automated: `harness-link.sh init ~/my-project --mode copy`. Run
`harness-link.sh update ~/my-project` later to see (and, after
confirming) apply upstream changes — it diffs your copy against the
current source first, so local edits aren't silently overwritten.

Manual, what that does under the hood:

```bash
cd ~/my-project
mkdir -p .claude
cp -r ~/agentharness/.claude/skills .claude/skills

# Record what you copied and from where, so future-you can diff and update
cat >> CLAUDE.md <<'EOF'

## Harness Integration
Copied from agentharness @ $(git -C ~/agentharness rev-parse --short HEAD)
- .claude/skills/ (committing, branching, python-conventions)
EOF
```

**Pros:** Independent of harness changes. **Cons:** Manual sync when the
harness improves (`harness-link.sh update` automates the sync itself, but
you still decide when to run it).

### Method 3: Git Submodule (for teams, or heavier integrations)

Automated: `harness-link.sh init ~/my-project --mode submodule` — adds
this harness as a submodule at `~/my-project/.agentharness` (pinned via
the submodule's own commit, not a mutable external path) and symlinks
skills from there.

Manual, what that does under the hood:

```bash
cd ~/my-project
git submodule add git@github.com:andr-ca/agentharness.git .agentharness
ln -s ../.agentharness/.claude/skills .claude/skills

# Update later:
git submodule update --remote .agentharness
```

**Pros:** Version-controlled, explicit pin. **Cons:** Submodule
operational overhead (contributors need `git submodule update --init`).

## Per-Component Integration

### Claude Code Skills

```bash
mkdir -p .claude/skills
ln -s ~/agentharness/.claude/skills/committing .claude/skills/committing
ln -s ~/agentharness/.claude/skills/branching .claude/skills/branching
ln -s ~/agentharness/.claude/skills/python-conventions .claude/skills/python-conventions
```

Verify: skills should appear when you run `/help` or reference them by
name in Claude Code.

### Language Guidelines

Only Python exists today (`languages/python/`). Reference it directly
rather than copying — conventions docs are meant to be read, not
vendored:

```markdown
<!-- In your project's CLAUDE.md -->
## Language Guide
Python conventions: see ~/agentharness/languages/python/CONVENTIONS.md
```

### Testing & Logging Patterns

```bash
cp ~/agentharness/patterns/testing/COMPLETION_CHECKLIST.md ./docs/
cp ~/agentharness/patterns/logging/logging.yaml.example ./config/logging.yaml
```

Then edit the copy — these are templates, not symlink targets, because
you'll customize thresholds and backends per project.

### Git Hook

```bash
git config core.hooksPath /path/to/agentharness/.github/hooks
```

Or copy it in so it travels with the project instead of depending on the
harness path:

```bash
mkdir -p .githooks
cp ~/agentharness/.github/hooks/prevent-trunk-commit .githooks/pre-commit
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

### `.gitignore`

```bash
cp ~/agentharness/.github/.gitignore.template .gitignore
```

## Project-Specific CLAUDE.md Template

```markdown
## Harness Integration

This project uses agentharness for:
- Skills: committing, branching, python-conventions (symlinked from .claude/skills/)
- Language: Python — see ~/agentharness/languages/python/CONVENTIONS.md
- Testing: patterns/testing/COMPLETION_CHECKLIST.md (copied to docs/)

Integration method: Symlinks
Location: ~/agentharness
Last synced: 2026-07-12 (commit abc1234)
```

## Keeping Projects Updated

All three modes: `harness-link.sh update ~/my-project` — shows what
changed (skills added/removed upstream; for copy mode, which files
diverged) and asks for confirmation before applying. `--yes` skips the
prompt for non-interactive use.

**Symlinks:** content is always current automatically; `update` only
matters here for picking up newly-added skills or a widened/narrowed
`--skills` filter.

**Copies:** `update` diffs your copy against the current source per
skill and only touches ones that actually changed.

**Submodules:** `update` re-syncs the skill symlinks the same way as
link mode; to also pull the submodule itself to the harness's latest
commit, run `git -C ~/my-project submodule update --remote .agentharness`
first (deliberately manual — the CLI won't move your pinned commit for
you without being asked).

## Troubleshooting

**Issue:** Skills not appearing in Claude Code
- Verify the symlink resolves: `ls -la .claude/skills/`
- Check the skill's `SKILL.md` has valid frontmatter

**Issue:** Symlink breaks when the harness moves
- Use an absolute path when creating the symlink, or move both together
- Consider the submodule method instead if the harness path isn't stable

**Issue:** `core.hooksPath` conflicts with an existing hook manager (husky, pre-commit)
- Only one `core.hooksPath` can be active. Either copy the harness hook's
  logic into your existing hook manager's config, or drop the other
  manager for this repo.

**Issue:** not sure what's actually installed, or whether it's still working
- `harness-link.sh status ~/my-project` shows what's recorded.
- `harness-link.sh doctor ~/my-project` validates it against reality
  (nonzero exit on any problem) — run this after moving the harness
  checkout, after a manual edit to `.claude/skills/`, or in your own CI.

**Issue:** integrated by hand (not via `harness-link.sh`) and want to switch to it
- There's no import path for a manual integration's state — run
  `harness-link.sh init` fresh; it's safe to re-run over an existing
  manual symlink setup that matches its own layout, but check `status`
  and `doctor` afterward rather than assuming it merged cleanly.

---

Once `frameworks/`, additional `languages/`, and `tools/` beyond
`tools/setup/` are built (see [ROADMAP.md](../ROADMAP.md)), this guide
will grow per-component sections for them. Until then, don't reference
paths that don't exist — check [MANIFEST.md](../MANIFEST.md) first.
