# Integration Guide – Using awesome-harness in Projects

Step-by-step guide for integrating components from awesome-harness into your projects.

## 📋 Integration Methods

### Method 1: Symlinks (Recommended for Active Development)

Keep your projects in sync with harness updates:

```bash
cd ~/my-project

# Link entire .claude directory
ln -s ~/awesome-harness/.claude .claude

# Or link specific skills
mkdir -p .claude/skills
ln -s ~/awesome-harness/.claude/skills/* .claude/skills/

# Link specific framework config
cp ~/awesome-harness/frameworks/react/tsconfig.json .
```

**Pros:** Always up-to-date, reduces duplication
**Cons:** Requires harness to be available locally

### Method 2: Copy (For Release Stability)

Lock to a specific version of harness components:

```bash
cd ~/my-project

# Copy skills to project
cp -r ~/awesome-harness/.claude/skills .claude/skills

# Copy framework configuration
cp -r ~/awesome-harness/frameworks/react/* .

# Commit to git with version reference
# In CLAUDE.md: harness v1.2.3 (commit abc123)
```

**Pros:** Version control, independence from harness updates
**Cons:** Manual sync when harness improves

### Method 3: Git Submodule (For Large Integrations)

Use git submodule for major component dependencies:

```bash
cd ~/my-project

# Add awesome-harness as submodule
git submodule add https://github.com/user/awesome-harness.git coding-harness

# Reference from submodule
ln -s coding-harness/.claude .claude
ln -s coding-harness/frameworks/react/tsconfig.json .

# Update in future
git submodule update --remote
```

**Pros:** Version controlled, clean git history
**Cons:** Additional git complexity

## 🚀 Per-Component Integration

### Integrating Claude Code Skills

```bash
# Option 1: Symlink all skills
ln -s ~/awesome-harness/.claude/skills ~/.claude/skills

# Option 2: Copy specific skills
cp ~/awesome-harness/.claude/skills/my-skill.md ~/.claude/skills/

# Verify in Claude Code
# Skills should appear in skill list
```

### Integrating Framework Configuration

```bash
# For React/Next.js project
cd ~/my-project

# Copy configuration files
cp ~/awesome-harness/frameworks/react/tsconfig.json .
cp ~/awesome-harness/frameworks/react/.eslintrc.json .
cp ~/awesome-harness/frameworks/react/next.config.js .

# Review and customize for your project
# Edit to match specific project needs
```

### Integrating Patterns

```bash
# Reference in your project's architecture documentation
# Link to specific patterns from awesome-harness

# Example in ARCHITECTURE.md:
# We use the error-handling pattern from awesome-harness:
# ~/awesome-harness/patterns/error-handling/README.md

# Copy pattern documentation for reference
cp ~/awesome-harness/patterns/error-handling/README.md ./docs/patterns/error-handling.md
```

### Integrating Language Guidelines

```bash
# Use language conventions in project CLAUDE.md
# Add to project/.claude/CLAUDE.md:

## Language Guide
Reference: ~/awesome-harness/languages/typescript/CONVENTIONS.md

## Naming Conventions
See awesome-harness TypeScript conventions for:
- camelCase for variables and functions
- PascalCase for types and classes
- UPPER_SNAKE_CASE for constants
```

### Integrating Tools

```bash
# Make tools available in project
cd ~/my-project

# Option 1: Symlink in package.json
"scripts": {
  "lint": "node ~/awesome-harness/tools/lint/custom-linter src"
}

# Option 2: Copy and customize
cp -r ~/awesome-harness/tools/lint ./tools/

# Option 3: Add to PATH
export PATH="$PATH:~/awesome-harness/tools/lint:~/awesome-harness/tools/build"
```

### Integrating Hooks

```bash
cd ~/my-project

# Install pre-commit hooks
mkdir -p .husky
cp ~/awesome-harness/hooks/pre-commit/* .husky/pre-commit

# Make executable
chmod +x .husky/pre-commit

# Or use husky
husky install
cp ~/awesome-harness/hooks/pre-commit/lint.sh .husky/pre-commit
```

## 📝 Project-Specific CLAUDE.md Template

Create a project-level CLAUDE.md that references the harness:

```markdown
# project-name – Claude Code Integration

Local Claude Code instructions for this project.

## Harness Integration

This project leverages awesome-harness for:

### Skills
- `/code-review-advanced` – From awesome-harness/.claude/skills/
- `/testing-strategy` – From awesome-harness/.claude/skills/

### Framework
- React/Next.js configuration from awesome-harness/frameworks/react/
- See frameworks/react/README.md for setup details

### Language
- TypeScript conventions from awesome-harness/languages/typescript/
- Follow CONVENTIONS.md for naming and style

### Patterns
- Error handling: ~/awesome-harness/patterns/error-handling/
- Testing: ~/awesome-harness/patterns/testing/

### Tools
- Linting: ~/awesome-harness/tools/lint/custom-linter
- Build: Custom scripts in ./scripts/

## Integration Method
[Symlinks / Copied / Submodule] from awesome-harness

Location: ~/awesome-harness
Version: [commit hash or version tag if applicable]

## Project-Specific Customizations
[Document any deviations from harness guidelines]

## How to Update
[Document how to pull latest from harness]
```

## 🔄 Keeping Projects Updated

### With Symlinks
Automatic – projects always use latest harness version.

### With Copies
Manual update needed:

```bash
# Update copied files
cp ~/awesome-harness/frameworks/react/tsconfig.json .

# Note in git commit
git commit -m "Update framework config from awesome-harness"
```

### With Submodules
Use git submodule update:

```bash
# Update submodule to latest
git submodule update --remote

# Or pin to specific commit
cd coding-harness && git checkout abc123 && cd ..
git add coding-harness
git commit -m "Pin awesome-harness to version X"
```

## ⚙️ Common Integration Patterns

### React/Next.js Project
```bash
# Framework config + TypeScript conventions + React patterns
ln -s ~/awesome-harness/.claude .claude
cp ~/awesome-harness/frameworks/react/{tsconfig,eslint,next}.* .
cp ~/awesome-harness/languages/typescript/CONVENTIONS.md ./docs/
```

### Django Project
```bash
# Framework config + Python conventions + API patterns
ln -s ~/awesome-harness/.claude .claude
cp -r ~/awesome-harness/frameworks/django/config/* .
cp ~/awesome-harness/languages/python/CONVENTIONS.md ./docs/
```

### Full Integration (All Components)
```bash
cd ~/my-project
ln -s ~/awesome-harness/.claude .claude
ln -s ~/awesome-harness/languages . docs/language-guide
cp ~/awesome-harness/frameworks/{framework}/* .
cp -r ~/awesome-harness/patterns ./docs/patterns
ln -s ~/awesome-harness/tools ./tools
```

## 🚨 Troubleshooting

**Issue:** Skills not appearing in Claude Code
- Solution: Verify symlink: `ls -la ~/.claude/skills/`
- Check skill file has proper frontmatter

**Issue:** Configuration conflicts with existing config
- Solution: Merge carefully, test after changes
- Keep backup of original config

**Issue:** Tools not in PATH
- Solution: Add to PATH: `export PATH="$PATH:~/awesome-harness/tools/lint"`
- Or use full paths in scripts

**Issue:** Symlinks break when harness moves
- Solution: Use absolute paths in symlinks
- Or move both together, update references

---

Choose the integration method that best fits your workflow and project needs.
