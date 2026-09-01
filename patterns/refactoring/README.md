# Refactoring

Safe, behavior-preserving code restructuring. This pattern applies when you need
to reorganize, rename, or reshuffle code without changing observable behavior or
public contracts.

**Read this before refactoring anything at Production tier.** Refactoring at
Prototype or Internal tier follows the same principles but with proportionally
less ceremony; see `.github/CODING_GUIDELINES.md#rigor-tiers`.

## The Core Contract: Behavior Preservation

Before you start, make one explicit choice:

1. **Is this refactoring, or a feature?**
   - **Refactoring:** Code behavior, observable interfaces, and test results
     remain identical before and after. Restructure, rename, decompose, or
     extract freely.
   - **Feature:** Behavior, performance, or public API changes. Requires a
     separate PR with test coverage and design review.

   If you're unsure, assume it's a feature (the conservative choice).

2. **Document what must not change:**
   - Public contracts (function signatures, REST endpoints, database schemas)
   - Performance characteristics (if any timing test exists, it must still pass)
   - Observable behavior (same output for the same input, same side effects)
   - Error modes (same errors thrown in the same conditions)

## Three Steps to Safe Refactoring

### 1. Characterization Tests Before Restructuring

Write tests that *capture* behavior as it exists today, without changing it.
This is different from unit tests — you're locking down the current contract
before touching the code.

```python
# ✅ Characterization test: capture behavior *as-is*
def test_find_user_empty_database_returns_none():
    """Lock down: empty database returns None, not an exception."""
    db = InMemoryDatabase()
    assert find_user(db, user_id=999) is None

def test_find_user_network_error_retries_once():
    """Lock down: transient network errors trigger one automatic retry."""
    db = MockDatabaseWithFail(fails_on_attempt=1)
    result = find_user(db, user_id=1)
    assert result.name == "Alice"  # Succeeds on retry
```

These tests are **not** assertions of ideal design — they're snapshots of
"here's what the code does today." Run them before refactoring starts to
verify they pass. During refactoring, they're your canary: if they break,
you've changed behavior, and that's either a feature (needs a separate PR) or
a bug in the refactor (fix it).

**When to write them:**
- Large refactors (restructuring multiple functions, extracting components)
- Changes to core algorithms or data structure handling
- Renaming public interfaces (functions, classes, REST endpoints)
- Anything that carries risk of unintended behavior change

**When you can skip them:**
- Obvious local-scope renames (renaming a loop variable)
- Extracting pure helper functions with no side effects
- Any change that the existing test suite already validates thoroughly

See `../testing/TDD.md` for test-writing practices.

### 2. Incremental Reversible Steps

Make refactoring commits small, logically independent, and reversible. If a
commit introduces a bug, rolling it back should be safe and leave the repo in
a working state.

```bash
# Good: reversible, logical steps
git log --oneline
# b7f42ac Extract parse_user_config() into separate function
# a9c8e1d Move config-loading logic to new module
# 2d15e8f Rename UserConfig.get_name() → UserConfig.name (property)
# 1e9a72c Update all call sites for new property
# c3f4b98 Delete old get_name() method

# Bad: monolithic, mixed concerns
# 8a1b2c3 Major refactor: extracted 5 files, renamed 20 functions, rewrote DB layer, updated tests
```

Each commit should:
- Change one logical thing (one extraction, one rename, one module move)
- Pass lint, types, and tests before and after
- Be self-contained (reverting it doesn't leave dangling references)

If you're splitting a file, extract the new file first, import from it, then
delete the old definition. Each step compiles/runs/tests.

### 3. Protected Public Contracts

Make explicit what the public contract is, and never change it during
refactoring.

**Public contracts are:**
- Function/method signatures (parameter names, types, return types)
- Class interfaces (public methods, attributes visible to callers)
- REST API endpoints (routes, request/response shapes, status codes)
- Database schemas (column names, types, constraints) — unless you're running
  a full migration with a schema version bump
- Exported modules and their names

**What you can change freely (internal details):**
- Private function/method names (anything `_prefixed` or `internal` in
  language idiom)
- Local variable names
- Function implementations and algorithms
- Internal class structure (fields that aren't part of the public interface)
- The order of code

**When changing a public contract, that's a feature**, not a refactor. Examples:
- Renaming a public function (use a deprecation pattern instead, or file a
  feature PR)
- Adding a required parameter to a public function
- Changing a REST endpoint route or response schema
- Splitting a table column into two

Document the deprecation path: old name stays as a wrapper calling the new
name, possibly with a warning log line. Deprecate over one release cycle;
remove in the next.

## Decision Tree

```
Starting a refactor?
├─ Is behavior observable anywhere changing?
│  ├─ Yes → Separate feature PR, not a refactor
│  └─ No → Proceed
├─ Is this low-risk?
│  ├─ Yes (obvious rename, local scope) → Commit directly
│  └─ No (algorithm, large extraction) → Write characterization tests first
├─ Write incremental commits
│  ├─ Each tests green before and after
│  ├─ Each is reversible
│  └─ Each is logically independent
└─ Verify: existing test suite still passes
   └─ Public contracts unchanged
```

## Common Refactoring Patterns

### Extract a Function

Before refactoring, ensure the function being extracted has a single,
well-defined purpose and is called from at least one place (or will be
called multiple times after extraction).

```python
# Before
def process_order(order):
    total = sum(item.price for item in order.items)
    tax = total * 0.08
    return total + tax

# Characterization test (locks down calculation)
def test_process_order_adds_8_percent_tax():
    order = Order([Item(price=100)])
    assert process_order(order) == 108.0

# After: extract tax calculation
def calculate_tax(subtotal):
    return subtotal * 0.08

def process_order(order):
    total = sum(item.price for item in order.items)
    tax = calculate_tax(total)
    return total + tax
```

Commit message: "Extract calculate_tax() function"

### Rename a Module

Rename the file first, update imports, verify tests pass, delete the old file.

```bash
# Step 1: Add new import path alongside old one
# (in new module) export everything the old module exported
# Commit: "Add new module path (alias for old module)"

# Step 2: Update call sites
# Commit: "Update imports to new module path"

# Step 3: Delete old module
# Commit: "Delete old module path (replaced by new path)"

# Each step: tests pass, nothing breaks
```

### Move a Function to a New Module

Extract the function to the new module first while keeping a wrapper in the
old module. Update callers. Remove the wrapper.

```python
# Step 1: Create new module with extracted function
# new_module.py:
def is_valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[1]

# Step 2: Update old module to import and re-export
# old_module.py:
from new_module import is_valid_email
# Keep old callers working

# Step 3: Update call sites
# Commit: "Update imports to new module"

# Step 4: Remove re-export
# Commit: "Remove re-export from old module (moved to new_module)"
```

## Rigor Tier Adjustments

**Production:** Write characterization tests for any refactor affecting >5
functions or a core algorithm. Incremental commits mandatory. Public contracts
must be preserved exactly.

**Internal:** Characterization tests for risky refactors. Incremental commits
recommended. Contracts can change if documented.

**Prototype:** No characterization tests required. Refactor freely. Contracts
can change without notice.

## See Also

- `../testing/TDD.md` — Test-first development and test structure
- `../testing/COVERAGE_REQUIREMENTS.md` — Coverage expectations
- `.github/CODING_GUIDELINES.md#rigor-tiers` — Tier definitions and contract
  binding
- `.claude/skills/code-review/SKILL.md` — Reviewing refactoring PRs for
  behavior changes
