---
name: refactoring
description: Use before restructuring code — covers behavior-preservation contracts, characterization tests, incremental reversible steps, and protected public contracts. Ensure refactoring remains a code change, not a feature change.
metadata:
  type: skills
  scope: ["Python", "Go", "JavaScript", "TypeScript", "Rust", "Java"]
  when: "Before refactoring; when restructuring code, renaming, extracting functions, or moving modules; when reviewing refactoring PRs"
---

# Refactoring Safely

Safe restructuring, behavior-preservation, protected contracts. A refactoring
**changes code structure, not behavior**. If behavior changes, that's a feature.

## One Core Rule: Behavior Preservation

Before you refactor, decide: **Am I changing code structure only, or am I
changing behavior?**

- **Refactoring:** Same inputs → same outputs. Same errors in same cases.
  Observable behavior identical. Only code structure changes.
- **Feature:** Behavior, performance, API, or error handling changes. Needs a
  separate PR with tests and design review.

If unsure, assume it's a feature (safer choice).

Document what *must not change*:
- Function/endpoint signatures
- Error modes (same exceptions in same conditions)
- Performance characteristics (if timing tests exist, they still pass)
- Database schemas (unless versioned migration)

## Three-Step Safe Refactoring

### 1. Characterization Tests (Before Touching Code)

Write tests that *capture* behavior as it is today — your safeguard against
accidentally changing something.

```python
# ✅ Characterization test: lock down current behavior
def test_find_user_missing_returns_none():
    """Current behavior: missing user returns None, not exception."""
    db = TestDatabase()
    assert find_user(db, 999) is None

def test_retry_once_on_network_error():
    """Current behavior: network errors trigger exactly one retry."""
    db = MockDB(fails_on_attempt=1)
    user = find_user(db, 1)
    assert user.id == 1  # Succeeds on retry
```

These tests answer: "What does this code actually do right now?" — not "what
should it do?" They're your canary: if they break during refactoring, you've
changed behavior (either a bug or a missed feature scope).

**When required (Production tier):** Large refactors (5+ functions, core
algorithms), renaming public interfaces, extracting components.

**When optional:** Obvious renames (loop variables), extracting pure helpers,
changes your existing test suite already covers.

### 2. Incremental Reversible Commits

One logical change per commit. Each passes tests before and after. Each is
reversible without leaving dangling references.

```
Good refactoring sequence:
1. Extract parse_config() to new function
2. Move config-loading to separate module
3. Rename UserConfig.get_name() → .name (property)
4. Update all call sites to use .name
5. Delete old get_name() method

Bad: One giant commit changing 20 things at once
```

Each commit:
- ✅ Compiles/runs/tests pass
- ✅ Logically independent
- ✅ Reversible (safe to `git revert`)
- ✅ Is one specific thing (one extraction, one rename, one module move)

### 3. Explicit Public Contracts

Never change these during refactoring:
- Function/method signatures (names, parameters, return types)
- Class public interfaces
- REST endpoint routes and response shapes
- Database schema column names
- Exported module names

**Changing a contract is a feature.** Use a deprecation pattern instead:

```python
# Old way (deprecated)
def get_user_name(user):
    return user.full_name

# New way
@deprecated("Use user.full_name directly")
def get_user_name(user):
    return user.full_name  # Thin wrapper, logs warning

# Later release: remove deprecated function
```

What *can* change freely (internal details):
- Private function/method names (`_prefixed`)
- Local variable names
- Implementation and algorithms
- Internal class fields
- Code organization

## Common Refactors

### Extract a Function

```python
# Before
def calculate_total(items):
    subtotal = sum(i.price for i in items)
    tax = subtotal * TAX_RATE
    return subtotal + tax

# Characterization test
def test_tax_calculation():
    items = [Item(100), Item(50)]
    assert calculate_total(items) == 162  # 150 * 1.08

# After
def calculate_tax(subtotal):
    return subtotal * TAX_RATE

def calculate_total(items):
    subtotal = sum(i.price for i in items)
    return subtotal + calculate_tax(subtotal)

# Test still passes ✓
# Commit: "Extract calculate_tax() function"
```

### Rename a Module

Move the file, update imports, verify tests, delete old file:

```bash
# 1. Create new_path/module.py, copy all exports
# 2. old_path/module.py: re-export from new path (compatibility)
# 3. Update call sites to import from new_path
# 4. Delete old_path/module.py

# Each step passes tests
```

### Rename a Public Function

Use a wrapper + deprecation (if you control all callers):

```python
# Step 1: Add new name as primary
def get_current_user(request):
    """Get the authenticated user from this request."""
    return extract_user_from_jwt(request.headers["authorization"])

# Step 2: Keep old name as deprecated alias
@deprecated("Use get_current_user()")
def current_user(request):
    return get_current_user(request)

# Step 3: Update callers
# Step 4: Later: remove old name
```

If you don't control all callers (public API), this is a breaking change —
not a refactor, a separate versioned release.

## Decision Tree

```
Refactoring?
├─ Is ANY observable behavior changing?
│  └─ Yes → That's a feature, separate PR
├─ Is this risky? (algorithm change, >5 functions, core module)
│  └─ Yes → Write characterization tests first
├─ Make commits small + reversible
│  └─ Each: test-passing, one logical thing, independent
└─ Public contracts: unchanged ✓
```

## Rigor Tiers

**Production:** Characterization tests for risky refactors. Incremental
commits. Contracts locked. Code review for safety.

**Internal:** Characterization tests for algorithm changes. Commits
recommended. Contracts can change if documented.

**Prototype:** No tests required. Refactor freely.

---

## See Also

- Full guide: `patterns/refactoring/README.md`
- Testing: `patterns/testing/TDD.md`, `patterns/testing/COVERAGE_REQUIREMENTS.md`
- Contracts: `.github/CODING_GUIDELINES.md#rigor-tiers`
- Reviewing refactors: `.claude/skills/code-review/SKILL.md`
