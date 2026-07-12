# tools – Utility Scripts & Tools

Standalone scripts, helpers, and utilities that improve development workflows.

## 📁 Tool Categories

- **lint/** – Custom linters and style checkers
- **build/** – Build automation and helpers
- **deploy/** – Deployment utilities and scripts

Add categories for other tools as discovered.

## 📦 What Each Tool Should Include

```
tools/{tool-category}/{tool-name}/
├── README.md           # Purpose and usage
├── index.js|py|sh      # Main executable
├── config/             # Configuration templates
└── examples/           # Usage examples
```

## 📝 Tool Template

When adding a tool, include:

1. **Purpose** – What problem does it solve?
2. **Installation** – How to install/use it
3. **Usage** – Command-line interface or API
4. **Configuration** – Setup options
5. **Examples** – Real-world usage examples
6. **Dependencies** – What it requires
7. **Exit Codes** – What different outputs mean

## 🔗 Linking to Tools

Tools can be referenced as:
- Symlinks in project directories
- npm/pip package scripts
- Git hooks
- CLI utilities

Example setup:
```bash
# Make available globally
ln -s ~/agentharness/tools/lint/custom-linter /usr/local/bin/lint-custom

# Use in package.json
"scripts": {
  "lint": "node ~/agentharness/tools/lint/custom-linter"
}

# Use in .husky hooks
#!/bin/bash
~/agentharness/tools/lint/custom-linter
```

## 📝 Adding a New Tool

1. Create a subdirectory under the appropriate category
2. Write a clear README
3. Create the main executable
4. Include configuration templates
5. Add working examples
6. Document dependencies
7. Test thoroughly before committing

## 🎯 Tool Categories Guide

### lint/
Custom linters, formatters, and style checkers:
- Language-specific formatters
- Custom rule implementations
- Multi-file linters

### build/
Build automation and compilation helpers:
- Build scripts
- Optimization utilities
- Build configuration templates

### deploy/
Deployment and release utilities:
- Deployment scripts
- Release automation
- Environment setup helpers

---

Tools should be self-contained and well-documented so they can be easily integrated into any project.
