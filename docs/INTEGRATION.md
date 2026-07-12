# Integration Guide – Using agentharness in Projects

Step-by-step guide for integrating components from agentharness into your
projects. Every command below is tested against what actually exists in
this repo today — see [MANIFEST.md](../MANIFEST.md) for the inventory.

## The Fast Path

```bash
~/agentharness/tools/setup/harness-link.sh /path/to/your-project
```

This symlinks `.claude/skills/`, copies `.github/.gitignore.template` to
`.gitignore` (merging if one exists), and optionally installs the
trunk-protection hook. See the script's `--help` for flags. Everything
below is the manual, step-by-step version of what that script does.

## Integration Methods

### Method 1: Symlinks (recommended for active development)

Keep your project in sync with harness updates automatically.

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
harness improves.

### Method 3: Git Submodule (for teams, or heavier integrations)

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

**Symlinks:** automatic — always current.

**Copies:**
```bash
cp ~/agentharness/patterns/logging/logging.yaml.example ./config/logging.yaml
git commit -am "Update logging config template from agentharness"
```

**Submodules:**
```bash
git submodule update --remote .agentharness
git add .agentharness
git commit -m "Update agentharness submodule"
```

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

---

Once `frameworks/`, additional `languages/`, and `tools/` beyond
`tools/setup/` are built (see [ROADMAP.md](../ROADMAP.md)), this guide
will grow per-component sections for them. Until then, don't reference
paths that don't exist — check [MANIFEST.md](../MANIFEST.md) first.
