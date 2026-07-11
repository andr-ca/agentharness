# GitHub Copilot Instructions for Python

> These are general Python engineering instructions. Repository-specific configuration,
> documentation, established conventions, and user requirements take precedence.

## 1. Core Operating Principles

- Understand the repository before changing it.
- Follow existing architecture, naming, test patterns, and tooling unless the task explicitly requires changing them.
- Keep changes focused on the requested behavior. Do not perform unrelated refactors, renames, dependency upgrades, or formatting sweeps.
- Prefer the smallest complete solution that preserves existing behavior and public contracts.
- Search for existing utilities, abstractions, patterns, and extension points before introducing new ones.
- Do not duplicate functionality that the repository already provides.
- Treat tests, linting, formatting, typing, generated artifacts, and documentation as part of the implementation—not optional follow-up work.
- Never claim that a command passed unless it was actually run successfully.
- If a required command cannot be run, state exactly what was not run and why.
- Do not hide failures by weakening tests, suppressing diagnostics, broadening exception handling, or disabling validation.

## 2. Inspect the Repository First

Before writing code, inspect the relevant project files and nearby implementation:

- `pyproject.toml` – Project metadata, dependencies, tool configuration
- `uv.lock`, `poetry.lock`, `pdm.lock`, `Pipfile.lock`, or requirements files – Lock files define exact dependencies
- `README.md`, `CONTRIBUTING.md`, `DEVELOPMENT.md` – Documentation and contribution guidelines
- `.github/copilot-instructions.md` and `.github/instructions/` – Repository-specific AI guidance
- `Makefile`, `justfile`, `tox.ini`, `noxfile.py` – Task runners and automation
- `.pre-commit-config.yaml` or equivalent – Pre-commit hooks and validation
- CI workflows under `.github/workflows/` – Build and test automation
- Existing tests for the affected component – Test patterns and coverage
- Neighboring modules that solve similar problems – Reusable patterns
- Code-generation configuration and migration tooling – Avoid manual edits of generated files
- The package's supported Python versions – Compatibility requirements

Derive commands and conventions from the repository rather than guessing them.

When multiple instruction files apply, follow the most specific applicable instruction. Do not override explicit repository conventions with generic preferences from this file.

## 3. Repository Navigation and Change Planning

- Locate the public entry point, implementation, tests, and configuration relevant to the requested behavior.
- Trace callers and consumers before changing a public function, class, protocol, schema, event, CLI option, or data model.
- Identify whether the affected files are handwritten, generated, vendored, or migration-controlled.
- Read enough surrounding code to understand invariants and error-handling behavior.
- For defects, identify or create a test that reproduces the failure before or alongside the fix.
- For non-trivial work, define the expected behavior and validation approach before implementation.
- Prefer symbol-aware navigation and precise searches over reading or rewriting large unrelated files.

## 4. Scope and Change Discipline

- Keep diffs narrow and intentional.
- Avoid opportunistic cleanup unrelated to the requested change.
- Do not rename public symbols, move modules, or alter package structure without a task-specific reason.
- Preserve backward compatibility unless a breaking change is explicitly requested.
- Preserve serialization formats, database schemas, CLI behavior, configuration keys, and public exception behavior unless intentionally changed.
- Do not change unrelated formatting.
- Do not modify lock files unless dependency metadata changed or the repository workflow requires regeneration.
- Do not modify generated files directly when a generator or source schema exists.
- Do not rewrite existing migrations after they may have been released or applied.
- Avoid adding dependencies when the standard library or an existing dependency reasonably solves the problem.
- Avoid speculative abstractions. Introduce an abstraction only when it represents a real boundary or repeated need.

## 5. Python Version and Compatibility

- Use syntax and standard-library APIs supported by the minimum Python version declared by the project.
- Check `requires-python`, classifiers, CI matrices, and type-checker configuration before using newer language features.
- Do not silently raise the minimum supported Python version.
- Preserve compatibility across the repository's supported Python versions.
- Prefer modern syntax only when supported by the project:
  - `list[str]` instead of `typing.List[str]` (requires Python 3.9+)
  - `dict[str, int]` instead of `typing.Dict[str, int]` (requires Python 3.9+)
  - `X | None` instead of `Optional[X]` (requires Python 3.10+)
  - `collections.abc` for runtime collection protocols
- Use `from __future__ import annotations` only when consistent with project policy or needed for supported versions.

## 6. Formatting, Linting, and Style

- Treat `pyproject.toml` and repository tool configuration as authoritative.
- Use the configured formatter (typically Ruff format or Black).
- Use the configured linter (typically Ruff).
- Use the configured import sorter; do not manually fight its output.
- Do not hard-code a line length if the repository already configures one.
- Avoid disabling lint rules globally to solve a local issue.
- Use a targeted suppression only when the code is correct, the rule is inappropriate, and the reason is documented.
- Prefer fixing the underlying code over adding `# noqa`, `# type: ignore`, or equivalent suppressions.
- When a suppression is necessary, use the narrowest rule code and scope.
- Review automated fixes and generated diffs before accepting them.
- Match surrounding code when the repository intentionally differs from common defaults.

### Typical Commands

Run these only when they match repository configuration:

```bash
uv run ruff format .          # Format code
uv run ruff check .           # Lint code
uv run ruff check . --fix     # Auto-fix lint issues
```

Or with Poetry, PDM, or pip:

```bash
poetry run ruff format .
poetry run ruff check .
pdm run ruff format .
```

## 7. Testing

- Write tests that exercise the behavior you implement.
- Run tests locally before declaring work complete.
- Use the repository's test runner (typically pytest, tox, or nox).
- Place tests beside the code they test, or follow the repository's test structure.
- Do not weaken assertions or broaden exception handling to make tests pass.
- Verify that tests fail without your changes and pass with them.
- For new features, add tests that cover happy path, edge cases, and error conditions.

Typical test commands:

```bash
pytest                        # Run all tests
pytest tests/                 # Run specific test directory
pytest -v                     # Verbose output
pytest --cov                  # With coverage
uv run pytest                 # With uv
```

## 8. Type Checking

- Run type checking if the repository uses a type checker (mypy, pyright, pytype).
- Treat type checking failures as errors equivalent to test failures.
- Prefer explicit type annotations for public APIs.
- Use `Any` sparingly and only when type cannot be properly expressed.
- Leverage TypeVar and Protocols for generic and structural typing.

Typical type-check commands:

```bash
mypy .
mypy --strict .
uv run mypy .
pyright .
```

## 9. Documentation and Docstrings

- Follow the repository's docstring convention (Google, NumPy, or Sphinx style).
- Write docstrings for public functions, classes, and modules.
- Include parameter descriptions, return types, and notable exceptions.
- Keep docstrings concise; extensive explanation belongs in guides or comments.
- Maintain existing docstring style consistency.
- For public APIs, document behavior, not implementation.

Example (Google style):

```python
def validate_email(address: str) -> bool:
    """Validate email address format.
    
    Args:
        address: Email address string to validate.
    
    Returns:
        True if valid email format, False otherwise.
    
    Raises:
        ValueError: If address is None or empty string.
    """
    if not address:
        raise ValueError("Address cannot be empty")
    return "@" in address
```

## 10. Dependencies and Imports

- Use explicit imports; avoid `import *`.
- Keep imports organized: standard library, third-party, local.
- Prefer the standard library when it adequately solves a problem.
- Avoid adding dependencies for small, single-purpose features.
- Pin dependency versions in `pyproject.toml` appropriately.
- Update lock files after changing dependencies.
- Document why a dependency is needed.

## 11. Error Handling

- Raise specific exceptions, not bare `Exception`.
- Catch only the exceptions you can handle.
- Preserve the original exception context with `raise ... from e`.
- Document raised exceptions in docstrings.
- Log errors with appropriate context before raising.
- Avoid broad `except:` or `except Exception:` unless there's a clear reason.

```python
# Good
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise ValueError("Failed to complete operation") from e

# Bad
try:
    result = risky_operation()
except:
    pass
```

## 12. Naming Conventions

- Use `snake_case` for functions, variables, and modules.
- Use `PascalCase` for classes and exceptions.
- Use `UPPER_SNAKE_CASE` for module-level constants.
- Use clear, descriptive names that explain purpose.
- Avoid single-letter names except for loop counters or mathematical variables.
- Avoid abbreviations; spell out words for clarity.

```python
# Good
user_count = 42
class UserRepository:
    pass

# Bad
uc = 42
class UR:
    pass
```

## 13. Code Organization

- Keep modules focused on a single responsibility.
- Group related functionality into classes or modules.
- Use `__all__` to define public API for modules.
- Organize code within a module: imports, constants, classes, functions.
- Use private methods/variables (prefix with `_`) for internal implementation.
- Avoid deeply nested structures; extract helper functions.

## 14. Common Pitfalls

### Mutable Default Arguments

```python
# Bad
def append_item(item, container=[]):
    container.append(item)
    return container

# Good
def append_item(item, container=None):
    if container is None:
        container = []
    container.append(item)
    return container
```

### Not Using Context Managers

```python
# Bad
f = open('file.txt')
content = f.read()
f.close()

# Good
with open('file.txt') as f:
    content = f.read()
```

### Bare `except` Clauses

```python
# Bad
try:
    do_something()
except:
    pass

# Good
try:
    do_something()
except SpecificError as e:
    handle_error(e)
```

### Using `is` for Value Comparison

```python
# Bad
if user_id is 5:
    pass

# Good
if user_id == 5:
    pass
```

### Global State

```python
# Bad
database_connection = None
def get_db():
    global database_connection
    if database_connection is None:
        database_connection = connect()
    return database_connection

# Good
class DatabaseManager:
    def __init__(self):
        self.connection = None
    def get_connection(self):
        if self.connection is None:
            self.connection = connect()
        return self.connection
```

## 15. Summary Checklist

Before declaring work complete:

- [ ] Changes are focused on the requested behavior
- [ ] Existing tests pass
- [ ] New tests added for new behavior
- [ ] Code follows repository's style and conventions
- [ ] Type checking passes (if applicable)
- [ ] Formatting and linting pass
- [ ] Docstrings added for public APIs
- [ ] No unnecessary dependencies added
- [ ] Backward compatibility preserved (unless breaking change requested)
- [ ] Documentation updated if behavior changed
- [ ] Commands were actually run (not claimed without execution)

---

**Last Updated:** 2026-07-11  
**Reference:** See `languages/python/CONVENTIONS.md` for additional Python-specific guidelines
