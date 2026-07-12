# Documentation – agentharness Guides

Comprehensive guides for understanding and using the agentharness repository.

## 📚 Documentation Index

### Quick Start
- **[Main README](../README.md)** – Repository overview and structure
- **[CLAUDE.md](../CLAUDE.md)** – Claude Code integration instructions

### Detailed Guides
- **[INTEGRATION.md](./INTEGRATION.md)** – How to use harness in your projects
  - Symlink vs. Copy vs. Submodule
  - Per-component integration steps
  - Keeping projects updated
  - Integration patterns by tech stack

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** – Technical design and philosophy
  - Design principles
  - Layered architecture
  - Component categories
  - Dependency management
  - Scaling considerations

## 🎯 Finding What You Need

### "I'm starting a new project"
1. Read: Main README for directory structure overview
2. Choose: Framework from `frameworks/` directory
3. Follow: INTEGRATION.md for setup steps
4. Reference: Language guidelines from `languages/`

### "I want to improve my coding practices"
1. Check: Language guidelines in `languages/{language}/`
2. Review: Patterns in `patterns/`
3. Copy: Relevant framework setup in `frameworks/`
4. Use: Claude Code skills from `.claude/skills/`

### "I need to integrate harness into a project"
1. Read: INTEGRATION.md for methods and steps
2. Choose: Symlink for development, copy for stability
3. Customize: Project-specific CLAUDE.md
4. Reference: Framework and language guides

### "I want to understand the overall design"
1. Read: ARCHITECTURE.md for philosophy and structure
2. Study: How components connect
3. Understand: Integration patterns
4. Plan: How to extend with new content

### "I want to add a new component"
1. Understand: ARCHITECTURE.md principles
2. Follow: Guidelines in relevant directory README
3. Document: With examples and metadata
4. Test: Before committing to harness

## 📁 Component Documentation

Each component type has its own README:

| Directory | README | Purpose |
|-----------|--------|---------|
| `.claude/` | [README](./.claude/README.md) | Claude Code assets |
| `frameworks/` | [README](../frameworks/README.md) | Framework-specific harnesses |
| `languages/` | [README](../languages/README.md) | Language conventions |
| `patterns/` | [README](../patterns/README.md) | Reusable patterns |
| `tools/` | [README](../tools/README.md) | Utility scripts |
| `hooks/` | [README](../hooks/README.md) | Automation hooks |

Click through to each for specific guidance on that component type.

## 🚀 Common Workflows

### Setting Up a New React Project
```bash
# 1. Read quick start
cat ../README.md

# 2. Review React harness
cat ../frameworks/react/README.md

# 3. Follow integration guide
cat ./INTEGRATION.md

# 4. Check TypeScript conventions
cat ../languages/typescript/CONVENTIONS.md

# 5. Reference patterns
ls ../patterns/
```

### Adding a New Framework Harness
```bash
# 1. Understand architecture
cat ./ARCHITECTURE.md

# 2. Review framework directory structure
ls ../frameworks/{example}/

# 3. Create new framework directory
mkdir -p ../frameworks/{new-framework}/

# 4. Follow framework README guidelines
cat ../frameworks/README.md
```

### Contributing a New Pattern
```bash
# 1. Understand pattern design
cat ../patterns/README.md

# 2. Review existing patterns for reference
ls ../patterns/*/

# 3. Create new pattern directory
mkdir -p ../patterns/{new-pattern}/

# 4. Document following pattern template
# See PATTERNS.md for template
```

## 🔍 How Documentation is Organized

```
docs/
├── README.md                    # This file (navigation hub)
├── INTEGRATION.md               # How to use in projects
└── ARCHITECTURE.md              # Design and philosophy

Plus in component directories:
  frameworks/README.md
  languages/README.md
  patterns/README.md
  tools/README.md
  hooks/README.md
  .claude/README.md
```

**Philosophy:** Documentation lives close to the code it describes.

## 📖 Reading Guide

### First Time Users
1. ✅ Read: Main README.md (5 min)
2. ✅ Read: This page (5 min)
3. ✅ Skim: INTEGRATION.md for your tech stack (10 min)
4. ✅ Reference: Relevant framework/language guides

### Regular Users
1. 🔍 Search: Component directories for what you need
2. 📖 Reference: Component-specific README files
3. 💡 Contribute: Share improvements back to harness

### Maintainers
1. 📋 Review: ARCHITECTURE.md for design philosophy
2. 🔄 Manage: Component quality and versions
3. 📊 Monitor: Usage and relevance of components
4. 📝 Update: Documentation as harness evolves

## 🎓 Learning Resources

### Understanding Claude Code Integration
- See: CLAUDE.md for skills and hooks
- Read: `.claude/README.md` for assets structure
- Reference: Specific skill documentation

### Understanding Project Setup
- See: Framework README in `frameworks/{framework}/`
- Follow: Integration patterns in INTEGRATION.md
- Check: Language guides for code conventions

### Understanding Patterns
- See: Specific pattern in `patterns/{pattern}/`
- Read: Problem statement and trade-offs
- Study: Examples and implementation guide

## 🤝 Contributing to Documentation

When adding new components:
1. Write a README explaining the component
2. Include examples or templates
3. Link to related components
4. Add metadata/frontmatter
5. Update this index if adding new doc type

## ❓ FAQ

**Q: Where should I put my custom skills?**
A: In your project's `.claude/skills/` directory. Reference agentharness skills from there.

**Q: Can I modify harness components?**
A: Yes, make copies and customize for projects. Improvements should be contributed back.

**Q: How do I stay updated?**
A: Use symlinks (auto-update) or regularly check for improvements if using copies.

**Q: Where are framework setup templates?**
A: In `frameworks/{framework}/` with README explaining what's included.

**Q: How do I report improvements?**
A: Add to harness (if applicable to multiple projects) or document in project CLAUDE.md.

---

**Start Here:** [README.md](../README.md) → [CLAUDE.md](../CLAUDE.md) → [INTEGRATION.md](./INTEGRATION.md)
