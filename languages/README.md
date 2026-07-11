# languages – Language-Specific Guidelines

Language-specific conventions, idioms, best practices, and style guidelines.

## 📁 Language Directories

- **typescript/** – TypeScript conventions and best practices
- **python/** – Python conventions and idioms
- **go/** – Go/Golang conventions
- **rust/** – Rust idioms and patterns

Add directories for other languages as needed.

## 📦 What Each Language Directory Should Contain

```
languages/{language}/
├── README.md              # Language overview and philosophy
├── CONVENTIONS.md         # Naming conventions and style
├── IDIOMS.md              # Language-specific idioms
├── TOOLING.md             # Recommended tools and setup
├── LIBRARIES.md           # Recommended libraries
└── ANTI_PATTERNS.md       # Common pitfalls to avoid
```

## 📝 Convention Categories

### Naming Conventions
- Variable naming (camelCase, snake_case, PascalCase)
- Function naming
- Class and type naming
- Constants and enums
- File and directory naming

### Code Style
- Indentation and whitespace
- Line length limits
- Formatting rules
- Comment style

### Best Practices
- Error handling approaches
- Memory management (if applicable)
- Concurrency patterns
- Testing conventions

### Recommended Tools
- Formatters and linters
- Type checkers
- Build tools
- Test frameworks
- Package managers

## 🔗 Linking Framework-Specific Variations

Language guidelines are extended with framework-specific details:
- React-specific TypeScript conventions → `frameworks/react/CONVENTIONS.md`
- Django-specific Python patterns → `frameworks/django/PATTERNS.md`

## 📝 Adding a New Language

1. Create directory: `languages/{language-name}/`
2. Write README describing language philosophy
3. Document naming and style conventions
4. List common idioms
5. Recommend tools and libraries
6. Note common anti-patterns
7. Link to framework-specific variations

## 🎓 Using Language Guidelines

When coding in a language:
1. Reference `README.md` for overview
2. Check `CONVENTIONS.md` for style decisions
3. Review `IDIOMS.md` for language-specific patterns
4. Consult `LIBRARIES.md` for tool recommendations
5. Avoid patterns listed in `ANTI_PATTERNS.md`

---

These guidelines evolve as you gain experience with each language and discover new conventions.
