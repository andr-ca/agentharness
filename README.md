# awesome-harness

A centralized repository for maintaining coding agent skills, instructions, tools, agentic loops, hooks, and best practices across all frameworks, languages, and projects.

## 🎯 Purpose

This repository serves as a universal harness for:

- **Coding Agent Skills** – Reusable Claude Code skills and agentic tools
- **Instructions & Guidelines** – Project-agnostic best practices and conventions
- **Tools & Utilities** – Custom scripts, helpers, and extensions
- **Agentic Loops** – Autonomous workflows and automation patterns
- **Hooks** – Pre/post-commit hooks, build hooks, and event handlers
- **Configurations** – Shared configurations for various tools and frameworks

Instead of duplicating these across multiple projects, maintain them once here and reference them in specific project repositories.

## 📁 Directory Structure

```
awesome-harness/
├── README.md                    # This file
├── CLAUDE.md                    # Instructions for using this harness
├── .github/                     # GitHub-specific configurations
│   ├── workflows/              # CI/CD workflows (reusable)
│   └── hooks/                  # GitHub hooks and automation
├── .claude/                     # Claude Code specific assets
│   ├── agents/                 # Custom agent definitions
│   ├── skills/                 # Claude Code skills (superpowers)
│   └── hooks/                  # Claude Code hooks
├── .codex/                      # Anthropic Codex-specific configs
├── frameworks/                  # Framework-specific harnesses
│   ├── react/                  # React/Next.js harness
│   ├── vue/                    # Vue/Nuxt harness
│   ├── angular/                # Angular harness
│   ├── django/                 # Django harness
│   ├── express/                # Express/Node harness
│   ├── go/                     # Go/Golang harness
│   └── ...                     # Other frameworks
├── languages/                   # Language-specific best practices
│   ├── typescript/             # TypeScript conventions
│   ├── python/                 # Python conventions
│   ├── go/                     # Go conventions
│   └── ...                     # Other languages
├── patterns/                    # Architecture & design patterns
│   ├── agentic-loops/          # Autonomous workflow patterns
│   ├── error-handling/         # Error handling strategies
│   ├── testing/                # Testing patterns & fixtures
│   └── ...
├── tools/                       # Utility scripts and tools
│   ├── lint/                   # Custom linters & formatters
│   ├── build/                  # Build scripts
│   ├── deploy/                 # Deployment utilities
│   └── ...
├── hooks/                       # Reusable hook implementations
│   ├── pre-commit/             # Pre-commit hook scripts
│   ├── post-merge/             # Post-merge automations
│   └── ...
└── docs/                        # Additional documentation
    ├── ARCHITECTURE.md         # Harness architecture overview
    └── INTEGRATION.md          # How to integrate with projects
```

## 🚀 Quick Start

1. **Clone this repository** in your development environment:
   ```bash
   git clone <repo-url> ~/coding-harness
   ```

2. **Reference in projects** – Link specific harness components to your projects:
   - Copy relevant skills to `.claude/skills/`
   - Import hooks in your `.githooks/` or `.husky/`
   - Use framework-specific configs as templates

3. **Read CLAUDE.md** – Understand how to effectively use this harness in your workflows

## 📚 Organization by Type

### Skills & Agents
- Located in `.claude/agents/` and `.claude/skills/`
- Each skill is self-contained with frontmatter metadata
- Skills are tagged by domain (auth, testing, deployment, etc.)

### Framework-Specific Harnesses
- Navigate to `frameworks/{framework-name}/` for:
  - Recommended project structure
  - Tool configurations
  - Common patterns and utilities
  - Integration guides

### Language-Specific Guidelines
- Navigate to `languages/{language-name}/` for:
  - Naming conventions
  - Code style guidelines
  - Idiomatic patterns
  - Library recommendations

### Patterns & Best Practices
- General architectural patterns applicable across projects
- Agentic loop implementations
- Testing strategies
- Error handling approaches

## 🔗 Integration with Projects

Each project can reference this harness in several ways:

```bash
# Example: Using skills from this harness in a project
ln -s ~/coding-harness/.claude/skills ~/.claude/skills

# Example: Using hooks
ln -s ~/coding-harness/hooks/pre-commit/.git/hooks/pre-commit .git/hooks/pre-commit
```

See `docs/INTEGRATION.md` for detailed integration strategies.

## 🎓 Contributing

When adding new harnesses, skills, or patterns:

1. Follow the organizational structure above
2. Include clear documentation and examples
3. Add metadata/frontmatter to skills
4. Tag with applicable frameworks/languages
5. Document dependencies and prerequisites
6. Create an entry in the relevant index

## 📝 License

This harness is maintained for personal use across projects.

---

**Last Updated:** 2026-07-11  
**Maintainer:** @andrey
