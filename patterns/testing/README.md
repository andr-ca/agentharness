# Testing – Complete Testing Guide

Comprehensive guide to testing strategies, Test-Driven Development (TDD), and test coverage requirements.

## 📋 Documentation

### [TDD.md](./TDD.md) – Test-Driven Development
**Complete TDD methodology with practical examples**

- The Red-Green-Refactor cycle explained
- TDD in practice with real-world examples
- Testing patterns (unit, integration, E2E)
- Common TDD mistakes to avoid
- How to write effective tests
- TDD workflow examples

**READ THIS FIRST** before writing any code.

### [COVERAGE_REQUIREMENTS.md](./COVERAGE_REQUIREMENTS.md) – Mandatory Coverage Standards
**Enforcing minimum 80% test coverage**

- What counts as coverage (and what doesn't)
- Coverage tiers and requirements
- Measuring coverage by language
- Coverage in CI/CD pipelines
- Handling low coverage
- Code review checklist

**At Production tier, your code will not merge if coverage < 80%. See Rigor Tiers in `.github/CODING_GUIDELINES.md`.**

### [COMPLETION_CHECKLIST.md](./COMPLETION_CHECKLIST.md) – Never Skip These Steps
**Mandatory checklist before marking work complete**

- Run all tests (every single test must pass)
- Verify coverage >= 80%
- Run linting and formatting
- Test all edge cases
- Fix inherited failures (even if from others)
- Pre-PR verification steps
- Definition of done
- **FOR WEB UI: Playwright tests with screenshot verification required**

**Work is NOT done until all items pass.**

### [PLAYWRIGHT_UI_TESTING.md](./PLAYWRIGHT_UI_TESTING.md) – Mandatory UI Testing Framework
**Complete Playwright guide for web UI development**

- Playwright is MANDATORY for all web UI work
- Screenshot verification is REQUIRED
- Agent must review and approve all screenshots
- Testing multiple browsers (Chrome, Firefox, Safari, mobile)
- Responsive design testing
- Visual regression detection
- CI/CD integration for UI tests
- Cannot mark UI work complete without screenshot approval

**ALL WEB UI WORK MUST USE PLAYWRIGHT WITH SCREENSHOT VERIFICATION**

## 🚨 Critical Requirements

### 0. Web UI Testing with Playwright (MANDATORY FOR WEB UI)

**ALL web UI work MUST use Playwright:**
- ✅ Write tests BEFORE building UI (TDD)
- ✅ Screenshot verification in every test (visual regression detection)
- ✅ Agent MUST review and approve screenshots (non-negotiable)
- ✅ Test multiple browsers (Chrome, Firefox, Safari, mobile)
- ✅ Test responsive design (all screen sizes)
- ✅ No visual regressions (screenshots match expected appearance)

**At Production tier, UI work without Playwright + screenshot approval WILL NOT MERGE.**

### 1. Minimum 80% Test Coverage (MANDATORY)

This is non-negotiable. Every piece of code must have tests covering:
- ✅ Happy path (normal operation)
- ✅ Error cases (what goes wrong)
- ✅ Edge cases (boundaries, special values)
- ✅ Integration points (APIs, databases)

**Coverage < 80% = Code will not merge. Period.**

### 2. Test-First Development (MANDATORY)

Always write tests before code:

```
❌ Wrong: Write code, then write tests
✅ Right: Write test (RED), write code (GREEN), refactor (REFACTOR)
```

### 3. All Tests Must Pass (MANDATORY)

**NO SKIPPED TESTS**
**NO FAILING TESTS**
**NO EXCEPTIONS**

```bash
# Before you claim work is done:
pytest --verbose              # All tests run
# Output must show: PASSED, not SKIPPED or FAILED
```

### 4. No Lint Errors (MANDATORY)

```bash
# All linting must pass
ruff check .                   # Python
npm run lint                   # JavaScript
go vet ./...                   # Go
```

### 5. Edge Cases Always Tested (MANDATORY)

For every function/method, test:
- Empty input
- Null input
- Minimum value
- Maximum value
- Invalid input
- Concurrent access (if applicable)
- Large datasets (if applicable)

### 6. Fix Inherited Failures (MANDATORY)

If ANY test is failing, YOU must fix it:
- Even if you didn't write the code
- Even if someone else broke it
- This is a shared responsibility
- Document the fix in your PR

---

## Quick Start

### For New Features

1. **Write failing test** (RED)
   ```python
   def test_new_feature():
       result = new_feature(input_data)
       assert result == expected_output
   ```

2. **Write minimal code** (GREEN)
   ```python
   def new_feature(input_data):
       return expected_output
   ```

3. **Refactor** (REFACTOR)
   ```python
   def new_feature(input_data):
       # Clean implementation
       process = validate(input_data)
       return calculate(process)
   ```

4. **Test edge cases**
   ```python
   def test_new_feature_with_empty_input():
       ...
   def test_new_feature_with_invalid_input():
       ...
   ```

5. **Verify coverage**
   ```bash
   pytest --cov=src --cov-fail-under=80
   ```

### For Bug Fixes

1. **Write test that reproduces bug** (RED)
2. **Fix the code** (GREEN)
3. **Verify test passes**
4. **Add tests for similar edge cases**
5. **Verify coverage >= 80%**

### Before Marking Complete

```bash
# 1. Run all tests
pytest                                    # All tests pass

# 2. Check coverage
pytest --cov=src --cov-fail-under=80     # >= 80%

# 3. Format and lint
ruff format .
ruff check . --fix

# 4. Final verification
echo "✅ All checks passed - ready to push"
```

## Testing Pyramid

**Structure of your test suite:**

```
         E2E Tests (5%)
       /              \
      /   Integration  \
     /      Tests      \
    /       (25%)       \
   /______________________\
  |                        |
  |    Unit Tests (70%)    |
  |                        |
  |________________________|
```

### Unit Tests (70% of tests)
- Fast (<100ms)
- Isolated, no dependencies
- Test single function/method
- No database, no API calls

### Integration Tests (25% of tests)
- Medium speed (1-10s)
- Test components together
- Use test database/services
- Verify contracts between modules

### E2E Tests (5% of tests)
- Slow (10s+)
- Test complete workflows
- From user perspective
- Minimal E2E (critical paths only)

---

## Language-Specific Guides

### Python (pytest)

**Setup:**
```bash
pip install pytest pytest-cov pytest-mock
```

**Configuration:**
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-fail-under=80 --cov-report=html"
```

**Run tests:**
```bash
pytest                           # All tests
pytest -v                        # Verbose
pytest --cov=src                # With coverage
pytest -k "test_user"           # Specific tests
pytest --lf                      # Last failed
```

### TypeScript/JavaScript (Jest)

**Setup:**
```bash
npm install --save-dev jest ts-jest @types/jest
```

**Configuration:**
```json
{
  "jest": {
    "preset": "ts-jest",
    "collectCoverageFrom": ["src/**/*.ts"],
    "coverageThreshold": {
      "global": {
        "lines": 80,
        "statements": 80,
        "functions": 80,
        "branches": 80
      }
    }
  }
}
```

**Run tests:**
```bash
npm test                        # All tests
npm test -- --coverage         # With coverage
npm test -- --watch            # Watch mode
npm test -- testname           # Specific test
```

### Go

**Testing:**
```bash
go test ./...                  # All tests
go test -v ./...               # Verbose
go test -cover ./...           # With coverage
go test -race ./...            # Check for race conditions
```

**Coverage:**
```bash
go test ./... -cover -coverprofile=coverage.out
go tool cover -html=coverage.out
```

---

## Common Testing Patterns

### Mocking External Services

**Python:**
```python
from unittest import mock

@mock.patch('requests.get')
def test_fetch_user(mock_get):
    mock_get.return_value.json.return_value = {"id": 1}
    user = fetch_user("http://api.example.com/user/1")
    assert user["id"] == 1
```

**TypeScript:**
```typescript
jest.mock('axios');
const mockGet = axios.get as jest.MockedFunction<typeof axios.get>;

test('fetches user', async () => {
    mockGet.mockResolvedValue({ data: { id: 1 } });
    const user = await fetchUser('http://api.example.com/user/1');
    expect(user.id).toBe(1);
});
```

### Testing Exceptions

**Python:**
```python
import pytest

def test_raises_exception():
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises()
```

**TypeScript:**
```typescript
test('raises exception', () => {
    expect(() => functionThatRaises()).toThrow(ValueError);
    expect(() => functionThatRaises()).toThrow('Invalid input');
});
```

### Testing Async Code

**Python:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

**TypeScript:**
```typescript
test('async function', async () => {
    const result = await asyncFunction();
    expect(result).toBe(expected);
});
```

---

## Testing Checklist for PR Review

When reviewing code, verify:

- [ ] All tests pass (run locally)
- [ ] Coverage >= 80% (check report)
- [ ] No skipped tests (`@skip`, `.skip()`)
- [ ] Test names describe behavior
- [ ] Tests follow AAA pattern
- [ ] Edge cases tested
- [ ] Error cases tested
- [ ] Mocks are appropriate
- [ ] No implementation details in tests
- [ ] Tests are deterministic

**If ANY box is unchecked, request changes.**

---

## Coverage Tools by Language

| Language | Tool | Command |
|----------|------|---------|
| Python | pytest-cov | `pytest --cov=src --cov-fail-under=80` |
| Python | Coverage.py | `coverage run -m pytest; coverage report` |
| TypeScript/JS | Jest | `jest --coverage --collectCoverageFrom` |
| Go | built-in | `go test ./... -cover -coverprofile=out.txt` |
| Java | JaCoCo | Maven/Gradle plugin |
| C# | OpenCover | `OpenCover.Console -target:...` |
| Ruby | SimpleCov | Gem + configure in tests |

---

## Resources

- **[Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)** – Kent Beck (creator of TDD)
- **[Growing Object-Oriented Software Guided by Tests](https://www.amazon.com/Growing-Object-Oriented-Software-Guided-Tests/dp/0321503627)** – Steve Freeman, Nat Pryce
- **[Clean Code](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)** – Robert Martin (Chapter 9: Unit Tests)
- **[The Pragmatic Programmer](https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/)** – Hunt & Thomas
- **[Testing Pyramid](https://martinfowler.com/bliki/TestPyramid.html)** – Martin Fowler
- **[Test Desiderata](https://kentbeck.github.io/TestDesiderata/)** – Kent Beck

---

## Key Takeaways

### Testing is NOT Optional

- Testing is part of development, not optional cleanup
- Tests are part of the feature, not separate work
- Coverage < 80% means work is incomplete

### Test-First is Better

- Write tests before code (TDD)
- Tests drive better design
- Refactoring is safe with tests
- Bugs caught during development, not in production

### Edge Cases Matter

- Empty, null, min/max values
- Error conditions and exceptions
- Concurrent access and race conditions
- Integration with external systems

### Quality Metrics

- Coverage >= 80%: Mandatory minimum
- All tests pass: Non-negotiable
- No lint errors: Required
- Deterministic tests: Essential

### Work Definition

**DONE means:**
- ✅ Tests written and passing
- ✅ Coverage >= 80%
- ✅ Lint passes
- ✅ All edge cases tested
- ✅ Ready to merge

---

**Critical Requirement:** 80% minimum test coverage (MANDATORY)  
**Status:** Non-negotiable, applies to all code
