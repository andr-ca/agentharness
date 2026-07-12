---
name: test-coverage-requirements
description: Mandatory test coverage requirements (80% minimum) and enforcement
complexity: medium
frameworks: all
languages: all
---

# Test Coverage Requirements

Mandatory test coverage standards for all code in agentharness projects.

## 🚨 CRITICAL REQUIREMENT

**MINIMUM 80% TEST COVERAGE IS MANDATORY**

This applies to:
- ✅ ALL production code
- ✅ ALL libraries and utilities
- ✅ ALL frameworks used
- ✅ ALL agents and orchestrators

This DOES NOT apply to:
- ❌ Test code itself
- ❌ Generated code
- ❌ Third-party dependencies
- ❌ Configuration-only files

## Coverage Tiers

### Coverage Levels

```
100%         ⭐⭐⭐ Excellent (strive for this)
95-99%       ⭐⭐  Very Good (within reach)
80-94%       ✅    Acceptable (MINIMUM)
75-79%       ⚠️   Below Minimum (WILL NOT MERGE)
<75%         ❌    Unacceptable (REJECT)
```

### Code Status by Coverage

| Coverage | Status | Action |
|----------|--------|--------|
| 100% | Complete | Approve & merge |
| 95-99% | Excellent | Approve & merge, optional improvements |
| 80-94% | Acceptable | Approve & merge (meets requirement) |
| 75-79% | Below Min | Request additional tests |
| 50-74% | Incomplete | Request significant testing |
| <50% | Unacceptable | Reject, require rewrite |

## What Counts as Coverage

### ✅ COUNTS TOWARD COVERAGE

1. **Line Coverage**
   - Every line of code executed by at least one test
   - Includes normal operation and error paths

2. **Branch Coverage**
   - Every if/else branch executed
   - Every case in switch statements
   - Every ternary operator path

3. **Exception Handling**
   - try/catch blocks tested
   - Error conditions verified
   - Exception messages validated

4. **Edge Cases**
   - Boundary conditions (empty, null, min/max values)
   - Off-by-one errors
   - Unicode, special characters
   - Large data sets

5. **Integration Points**
   - API calls (mocked or real)
   - Database operations (with transactions)
   - External service calls
   - File I/O operations

### ❌ DOES NOT COUNT

1. **Impossible Code Paths**
   ```python
   # Only if truly unreachable:
   if False:  # pragma: no cover
       do_impossible_thing()
   ```

2. **Pure Boilerplate**
   - IDE-generated getters/setters (in some languages)
   - Auto-generated equals/hashCode (Java)
   - Marshaling code (with limitations)

3. **Comments and Docstrings**
   - Documentation alone doesn't count
   - But should be verified for accuracy

4. **Test Code**
   - Test fixtures don't need coverage
   - Test utilities don't need coverage
   - But test failures must be real

## Coverage by Type

### Unit Tests (Should be 70% of tests)

**Coverage target: 100% of logic**

```python
def is_valid_email(email):
    """Unit test should cover all branches."""
    return "@" in email and "." in email.split("@")[1]

# Tests needed:
# ✓ Valid email: "user@example.com"
# ✓ Missing @: "userexample.com"
# ✓ Missing domain: "user@"
# ✓ No dot in domain: "user@example"
# ✓ Empty string: ""
# ✓ Only @: "@"
# ✓ Only dot: "."
```

### Integration Tests (Should be 25% of tests)

**Coverage target: 80-90%**

```python
def test_user_creation_through_api():
    """Integration test covers happy path."""
    response = client.post("/api/users", {
        "email": "test@example.com",
        "password": "secure"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    
    # Verify database
    user = User.find_by_email("test@example.com")
    assert user is not None
```

### E2E Tests (Should be 5% of tests)

**Coverage target: Critical paths only**

```python
def test_complete_user_registration_flow():
    """E2E test covers end-to-end workflow."""
    # User visits site
    browser.get("/register")
    
    # User fills form
    browser.fill("email", "test@example.com")
    browser.fill("password", "secure")
    browser.click("Register")
    
    # User is logged in
    assert browser.current_url == "/dashboard"
```

## Measuring Coverage

### By Language

**Python (pytest + coverage):**
```bash
# Install
pip install pytest pytest-cov

# Run tests with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Check minimum coverage in CI
pytest --cov=src --cov-fail-under=80
```

**TypeScript/JavaScript (Jest):**
```bash
# Install
npm install --save-dev jest

# Run tests with coverage
npm test -- --coverage

# Check minimum coverage
npm test -- --coverage --collectCoverageFrom="src/**/*.ts"
```

**Go:**
```bash
# Run tests with coverage
go test ./... -cover -coverprofile=coverage.out

# View coverage
go tool cover -html=coverage.out

# Check minimum coverage
COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    echo "Coverage $COVERAGE% below minimum 80%"
    exit 1
fi
```

**Java (JaCoCo + Maven):**
```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.10</version>
    <executions>
        <execution>
            <id>check</id>
            <goals>
                <goal>check</goal>
            </goals>
            <configuration>
                <rules>
                    <rule>
                        <element>PACKAGE</element>
                        <minimum>0.80</minimum>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### Interpreting Coverage Reports

**Example report:**
```
File                          Coverage  Lines  Missing
─────────────────────────────────────────────────────
src/user/auth.py              95%       120    6
src/user/models.py            82%       45     8
src/user/validators.py        88%       60     7
─────────────────────────────────────────────────────
TOTAL                         88%       225    21
```

**What this means:**
- ✅ Overall 88% coverage (above 80% minimum)
- ✅ auth.py at 95% (excellent)
- ⚠️  validators.py at 88% (acceptable but could improve)
- ⚠️  models.py at 82% (just at minimum)

## Coverage in CI/CD

### GitHub Actions Example

```yaml
name: Tests & Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Run tests with coverage
        run: pytest --cov=src --cov-fail-under=80 --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
          verbose: true
```

### GitLab CI Example

```yaml
test:
  image: python:3.11
  script:
    - pip install -e ".[dev]"
    - pytest --cov=src --cov-fail-under=80 --cov-report=xml
  coverage: '/TOTAL\s+\d+\s+\d+\s+(\d+%)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## Handling Low Coverage

### When Coverage Falls Below 80%

**DO NOT:**
- ❌ Lower the coverage requirement
- ❌ Use `# pragma: no cover` to skip untested code
- ❌ Merge and "fix it later"
- ❌ Write tests that don't actually verify behavior

**DO:**
- ✅ Write tests for untested code
- ✅ Simplify overly complex code
- ✅ Break large functions into smaller ones
- ✅ Refactor to make code more testable
- ✅ Request reviewer help identifying what to test

### Code is Too Complex to Test

If code is hard to test, the code is the problem, not the tests.

```python
# ❌ Hard to test: too many responsibilities
def process_user_registration(data):
    validate_email(data['email'])
    user = create_user(data)
    send_welcome_email(user)
    log_registration(user)
    update_analytics(user)
    notify_admins(user)
    return user

# ✅ Easier to test: single responsibility
def process_user_registration(data, email_service, analytics):
    user = create_user_from_data(data)
    email_service.send_welcome(user)
    analytics.track_registration(user)
    return user
```

### Refactoring for Testability

If your code is hard to test:

1. **Break into smaller functions**
   - One function, one job
   - ~20 lines max per function
   - Single reason to change

2. **Reduce dependencies**
   - Inject dependencies (don't create them)
   - Make dependencies mockable
   - Avoid global state

3. **Simplify logic**
   - Extract complex conditions
   - Use early returns
   - Avoid nested loops/conditions

4. **Add clear contracts**
   - Document what function does
   - Make preconditions explicit
   - Handle edge cases explicitly

## Coverage Targets by Module Type

### Core Libraries

**Target: 95%+ coverage**

These are the foundation. Must be bulletproof.

```python
# src/utils/string_utils.py
# MUST be near 100% coverage
# Every function, every edge case tested
```

### Business Logic

**Target: 90%+ coverage**

Heart of the application. Thoroughly tested.

```python
# src/user/authentication.py
# MUST have comprehensive test suite
# All paths through auth logic tested
```

### Integrations & APIs

**Target: 85%+ coverage**

Integration points need testing (with mocks).

```python
# src/integrations/payment_gateway.py
# MUST test success and failure paths
# MUST mock external API calls
```

### Configuration & Utilities

**Target: 80%+ coverage**

Even configuration needs testing.

```python
# src/config.py
# MUST test loading, validation, defaults
```

### Never Below 80%

There are no exceptions. No module goes below 80%.

## Exception: Impossible Code Paths

Only use pragma comments for code that truly cannot be executed:

```python
# Acceptable (truly unreachable)
if sys.version_info >= (3, 10):
    new_feature()
else:  # pragma: no cover
    # This never runs in Python 3.11+ CI environment
    old_feature()

# Acceptable (defensive programming)
try:
    result = risky_operation()
except ImpossibleError:  # pragma: no cover
    # This should never happen but we defend against it
    log_critical_error()

# NOT ACCEPTABLE (hiding untested code)
def important_function():
    ...
    if never_happens:  # pragma: no cover
        critical_logic()
```

## Code Review Checklist

When reviewing code, verify:

### Coverage Verification
- [ ] All new code has tests
- [ ] Coverage report shows >= 80%
- [ ] No test code marked with pragma comments
- [ ] No skipped tests (@skip, pytest.mark.skip)

### Test Quality
- [ ] Tests verify behavior, not implementation
- [ ] Tests have clear, descriptive names
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] Tests are deterministic (not flaky)
- [ ] Tests are fast (<100ms for unit tests)

### Test Completeness
- [ ] Happy path tested
- [ ] Error cases tested
- [ ] Edge cases tested
- [ ] Boundary conditions tested
- [ ] Integration points mocked appropriately

### Code Quality
- [ ] Code is testable (not too complex)
- [ ] Functions are single responsibility
- [ ] Dependencies are injected
- [ ] No global state used

**If coverage < 80%, request changes before approval.**

## Benefits of 80% Coverage

| Aspect | Benefit |
|--------|---------|
| **Bug Prevention** | Regressions caught before merge instead of in production |
| **Refactoring Safety** | Can confidently change code |
| **Documentation** | Tests show how code works |
| **Design Quality** | Testable code is better designed |
| **Team Confidence** | Everyone can modify code safely |
| **Maintenance** | Less technical debt |
| **Reliability** | Fewer production issues |

## Resources

- [Istanbul Code Coverage](https://istanbul.js.org/) – JavaScript coverage tool
- [Coverage.py](https://coverage.readthedocs.io/) – Python coverage tool
- [JaCoCo](https://www.jacoco.org/) – Java coverage tool
- [Codecov](https://codecov.io/) – Coverage tracking service
- [Code Climate](https://codeclimate.com/) – Code quality metrics

---

**REMEMBER:** 80% is the MINIMUM. Strive for 95%+.

**Requirement Status:** MANDATORY, NON-NEGOTIABLE  
**See Also:** TDD.md, testing patterns
