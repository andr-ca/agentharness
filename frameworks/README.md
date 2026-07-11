# frameworks – Framework-Specific Harnesses

Framework-specific configurations, templates, best practices, and patterns.

## 📁 Framework Directories

- **react/** – React and Next.js harnesses
- **vue/** – Vue and Nuxt harnesses
- **angular/** – Angular harnesses
- **django/** – Django harnesses
- **express/** – Express.js and Node.js harnesses
- **go/** – Go/Golang harnesses

Add directories for other frameworks as needed.

## 📦 What Each Framework Directory Should Contain

```
frameworks/{framework}/
├── README.md              # Framework-specific overview
├── setup/                 # Initial setup templates
│   └── tsconfig.json     # Or relevant config files
├── patterns/             # Framework-specific patterns
├── examples/             # Working examples
├── tools/                # Framework-specific utilities
└── CONVENTIONS.md        # Style and naming conventions
```

## 🚀 Using a Framework Harness

When starting a new project in a framework:

```bash
# Copy configuration files
cp ~/awesome-harness/frameworks/{framework}/tsconfig.json .

# Review patterns and conventions
cat ~/awesome-harness/frameworks/{framework}/README.md

# Use examples as reference
ls ~/awesome-harness/frameworks/{framework}/examples/
```

## 📝 Adding a New Framework

1. Create a directory: `frameworks/{framework-name}/`
2. Add a README explaining the framework
3. Include setup templates and common configurations
4. Document patterns specific to this framework
5. Add examples showing best practices
6. Link to language-specific guidelines in `languages/`

---

Each framework should be relatively self-contained but reference shared patterns from `patterns/` directory.
