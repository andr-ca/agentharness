# .claude – Claude Code Assets

This directory contains Claude Code-specific configurations, skills, agents, and hooks.

## 📁 Structure

- **agents/** – Custom agent definitions and configurations
- **skills/** – Claude Code superpowers/skills for specialized tasks
- **hooks/** – Event handlers and automation scripts

## 🚀 Quick Setup

When using this in a project:

```bash
# Symlink to project
ln -s ~/awesome-harness/.claude ~/.claude

# Or selectively:
ln -s ~/awesome-harness/.claude/skills ~/.claude/skills
```

## 📝 How to Add Content

### Adding a Skill
Place a new skill in `skills/` with frontmatter metadata:

```yaml
---
name: my-skill-name
description: Brief description of what this skill does
metadata:
  type: skills
  complexity: medium
---

<skill content and instructions>
```

### Adding an Agent
Create agent definition in `agents/` following Claude Agent SDK structure.

### Adding a Hook
Place hook scripts in `hooks/` subdirectories (`pre-commit/`, `post-merge/`, etc.) with clear documentation.

---

See parent CLAUDE.md for integration instructions.
