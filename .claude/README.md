# .claude – Claude Code Assets

This directory contains Claude Code-specific skills.

## Structure

- **skills/** – Claude Code skills, loaded on demand (see `MANIFEST.md` at
  repo root for the current list)

`agents/` and `hooks/` are planned but not built yet — see
[ROADMAP.md](../ROADMAP.md).

## Quick Setup

In a **project** (not your home directory — see the warning below):

```bash
cd ~/my-project
mkdir -p .claude/skills
ln -s ~/agentharness/.claude/skills/committing .claude/skills/committing
ln -s ~/agentharness/.claude/skills/branching .claude/skills/branching
ln -s ~/agentharness/.claude/skills/python-conventions .claude/skills/python-conventions
```

⚠️ **Never** `ln -s ~/agentharness/.claude ~/.claude` — that replaces or
fights with your global Claude Code configuration, which almost certainly
has settings unrelated to this harness. Symlink into the project's
`.claude/`, one skill at a time or the whole `skills/` directory, not your
home directory.

## How to Add Content

### Adding a Skill

Place a new skill in `skills/{skill-name}/SKILL.md` with frontmatter:

```yaml
---
name: skill-name
description: Brief description of what this skill does and when it triggers
metadata:
  type: skills
  complexity: medium
---

<skill content and instructions>
```

See any existing skill under `skills/` for a working example.

---

See root [CLAUDE.md](../CLAUDE.md) for repo-wide rules and
[MANIFEST.md](../MANIFEST.md) for the current asset index.
