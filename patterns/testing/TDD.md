---
name: test-driven-development
description: Complete TDD methodology, workflow, and enforcing minimum 80% test coverage
complexity: medium
frameworks: all
languages: all
---

# Test-Driven Development (TDD)

Complete guide to Test-Driven Development as a foundational practice for all code in agentharness projects.

## 🚨 CRITICAL REQUIREMENT

**Minimum 80% test coverage is MANDATORY for all code.**

This is not optional, not negotiable, not "nice to have." Code without adequate test coverage is considered incomplete and will not be merged.

## Why TDD Is Non-Negotiable

### The Problem We're Solving

Without TDD:
- ❌ Bugs slip into production (no safety net)
- ❌ Refactoring becomes terrifying (might break something)
- ❌ Code architecture is often poor (not designed for testability)
- ❌ Time spent debugging exceeds time spent testing
- ❌ Technical debt accumulates rapidly
- ❌ New team members can't confidently change code

With TDD:
- ✅ Bugs caught during development (fast feedback)
- ✅ Refactoring is safe (tests verify behavior)
- ✅ Code architecture is clean (must be testable)
- ✅ Most time spent writing tests (prevents bugs upfront)
- ✅ Technical debt is prevented (tests enforce contracts)
- ✅ New developers can change code with confidence

## The TDD Cycle (Red-Green-Refactor)

### Step 1: RED – Write Failing Test

Write a test for a feature that doesn't exist yet.

```python
# ❌ This test fails (feature doesn't exist)
def test_user_can_authenticate_with_valid_credentials():
    user = authenticate(email="user@example.com", password="correct")
    assert user is not None
    assert user.email == "user@example.com"
```

**Why start with a failing test?**
- Proves the test is actually checking something
- Ensures the test would catch a bug (not a false positive)
- Clarifies what the feature should do
- Drives design from the user's perspective

### Step 2: GREEN – Write Minimal Code to Pass

Write the **smallest possible implementation** to make the test pass.

```python
# ✅ Minimal implementation to pass the test
def authenticate(email, password):
    if email == "user@example.com" and password == "correct":
        user = type('User', (), {})()
        user.email = email
        return user
    return None
```

**This is intentionally simple!** Don't over-engineer or add features. Just make the test pass.

### Step 3: REFACTOR – Clean Up Code

Now improve the code while keeping tests passing.

```python
# ✅ Refactored, still passes tests
class User:
    def __init__(self, email):
        self.email = email

def authenticate(email, password):
    if _validate_credentials(email, password):
        return User(email)
    return None

def _validate_credentials(email, password):
    # Simplified for example
    return email == "user@example.com" and password == "correct"
```

### Complete Cycle

```
RED          GREEN        REFACTOR      RED          GREEN        ...
(Write test) (Make pass)  (Clean up)    (Write test) (Make pass)
     ❌  →       ✅      →     ✅     →      ❌    →    ✅    →

Each cycle:
- Tests increase
- Code improves
- Confidence grows
- Bugs decrease
```

## TDD in Practice

### Rule 1: Test First, Always

**The Law of TDD:**
> You must not write production code before writing a failing test.

Timeline:
```
❌ Wrong approach
Time:  0 ────────── 5 ────────── 10 ────────── 15
       Code         Code         Tests        Tests
       (WRONG!)     (feature)    (late!)      (insufficient)

✅ Correct approach  
Time:  0 ── 1 ── 2 ── 3 ── 4 ── 5 ── 6 ── 7 ── 8
       Test Test Code Test Code Code Test Code
       (RED) (RED) (GREEN) (GREEN) (GREEN) (REFACTOR) (PASS) (DONE)
```

### Rule 2: One Test at a Time

```python
# ❌ DON'T: Write multiple tests at once
def test_user_authentication():
    # Multiple unrelated assertions
    user = authenticate("user@example.com", "password")
    assert user is not None
    assert user.email == "user@example.com"
    assert user.created_at is not None
    assert user.profile is not None
    # ... 10 more assertions

# ✅ DO: Write one test per behavior
def test_authenticate_returns_user_on_valid_credentials():
    user = authenticate("user@example.com", "correct_password")
    assert user is not None

def test_authenticate_returns_none_on_invalid_credentials():
    user = authenticate("user@example.com", "wrong_password")
    assert user is None

def test_authenticate_returns_user_with_correct_email():
    user = authenticate("user@example.com", "correct_password")
    assert user.email == "user@example.com"
```

### Rule 3: Keep Tests Simple and Fast

```python
# ❌ DON'T: Complex, slow tests
def test_user_authentication():
    # Hits real database (slow!)
    database.connect()
    user_id = database.create_user("user@example.com", "password")
    time.sleep(5)  # Waiting for email
    result = authenticate("user@example.com", "password")
    database.delete_user(user_id)  # Cleanup
    assert result is not None

# ✅ DO: Simple, fast tests with mocks
@mock.patch('database.check_credentials')
def test_user_authentication(mock_check):
    mock_check.return_value = True
    user = authenticate("user@example.com", "password")
    assert user is not None
    mock_check.assert_called_once_with("user@example.com", "password")
```

### Rule 4: Test Behavior, Not Implementation

```python
# ❌ DON'T: Test implementation details
def test_password_is_hashed():
    user = User(password="secret")
    # Testing HOW it's done, not WHAT it does
    assert user._password_hash != "secret"
    assert user._salt is not None

# ✅ DO: Test the contract (what it does)
def test_user_password_cannot_be_retrieved():
    user = User(password="secret")
    # Testing THAT it works, not HOW
    with pytest.raises(AttributeError):
        _ = user.password  # Can't get original password

def test_authentication_fails_with_wrong_password():
    user = User(password="secret")
    assert not user.verify_password("wrong")
```

### Rule 5: Arrange-Act-Assert (AAA)

Structure every test with three clear sections:

```python
def test_discount_calculation():
    # ARRANGE: Set up test data
    cart = Cart()
    cart.add_item(Product("Widget", 100), quantity=2)
    
    # ACT: Perform the action being tested
    discount = cart.calculate_discount(coupon_code="SAVE20")
    
    # ASSERT: Verify the result
    assert discount == 40  # 20% of 200
```

## Test Coverage Requirements

### Minimum 80% Coverage Requirement

**This is a hard requirement, not a guideline.** For the coverage tiers,
what counts, and per-language measurement commands, see
`COVERAGE_REQUIREMENTS.md` — that file owns this policy; it's not
restated here to avoid the two versions drifting apart.

This section (and this file generally) applies at the **Production**
rigor tier. See `.github/CODING_GUIDELINES.md#rigor-tiers` for what
applies to prototypes and internal tools instead.

### What Counts Toward Coverage

✅ **COUNTS:**
- Line coverage (every line executed by tests)
- Branch coverage (every if/else path tested)
- Function/method execution
- Exception handling paths
- Edge cases and boundary conditions

❌ **DOES NOT COUNT:**
- Lines marked with `# pragma: no cover` (only for impossible paths)
- IDE autocomplete in test files
- Typing annotations alone
- Comments

### Measuring Coverage

**Python:**
```bash
# Run tests with coverage
pytest --cov=src --cov-report=html

# Check coverage in CI
pytest --cov=src --cov-fail-under=80
```

**TypeScript/JavaScript:**
```bash
# Jest coverage
jest --coverage --coverageThreshold='{"global":{"branches":80,"functions":80,"lines":80,"statements":80}}'

# Check coverage
jest --coverage --testPathPattern="src"
```

**Go:**
```bash
# Generate coverage report
go test ./... -cover -coverprofile=coverage.out

# View coverage
go tool cover -html=coverage.out
```

### Coverage in CI/CD

All projects MUST enforce coverage checks in CI:

**GitHub Actions example:**
```yaml
- name: Run tests with coverage
  run: pytest --cov=src --cov-fail-under=80

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
    fail_ci_if_error: true
```

**Fail the build if coverage < 80%:**
```bash
# In your CI configuration
pytest --cov=src --cov-fail-under=80 --cov-report=term-missing
```

## Testing Patterns

### 1. Unit Tests (Fast, Isolated)

Test a single function/method in isolation.

```python
# Test only the function, nothing else
def test_calculate_total_price():
    # No database, no API calls
    price = calculate_total(items=[
        {"price": 10, "qty": 2},
        {"price": 5, "qty": 3}
    ])
    assert price == 35
```

**Target: 70% of tests should be unit tests**

### 2. Integration Tests (Realistic, Slower)

Test multiple components working together.

```python
def test_user_can_checkout_with_payment():
    # Creates actual order, processes payment
    user = User.create(email="test@example.com")
    cart = Cart(user)
    cart.add(Product(price=50))
    
    order = cart.checkout(payment_method="card")
    
    assert order.id is not None
    assert order.status == "completed"
    assert Payment.for_order(order.id).status == "processed"
```

**Target: 25% of tests should be integration tests**

### 3. End-to-End Tests (Realistic, Slowest)

Test complete workflows as a user would experience.

```python
def test_user_registration_to_first_purchase():
    # This tests the entire flow
    browser.navigate_to("/")
    browser.click("Sign Up")
    browser.fill("email", "user@example.com")
    browser.fill("password", "secure_password")
    browser.click("Create Account")
    
    assert browser.current_url == "/dashboard"
    
    browser.click("Shop")
    browser.click_product("Widget")
    browser.click("Add to Cart")
    browser.click("Checkout")
    
    assert browser.find("Order Confirmation") is not None
```

**Target: 5% of tests should be E2E tests**

### 4. Edge Cases and Error Conditions

Test what happens when things go wrong.

```python
def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_authenticate_with_empty_email():
    with pytest.raises(ValueError, match="email required"):
        authenticate("", "password")

def test_handle_network_timeout():
    mock_request.side_effect = TimeoutError()
    result = fetch_data()
    assert result == cached_value  # Falls back to cache
```

## TDD Workflow Example

Let's build a complete feature using TDD.

### Feature: User Password Reset

**Requirement:** Users can reset their password by email.

### Test 1: Request Password Reset

```python
# RED: Test that doesn't exist yet
def test_user_can_request_password_reset():
    user = User(email="user@example.com")
    
    result = request_password_reset(user.email)
    
    assert result.success == True
    assert result.message == "Reset link sent to your email"
```

### Implement Minimal Code

```python
# GREEN: Make it pass (minimal)
def request_password_reset(email):
    result = type('Result', (), {})()
    result.success = True
    result.message = "Reset link sent to your email"
    return result
```

### Test 2: Reset Token Created

```python
# RED: More specific test
def test_password_reset_token_is_created():
    user = User(email="user@example.com")
    
    request_password_reset(user.email)
    
    token = PasswordResetToken.find_by_user(user)
    assert token is not None
    assert token.is_valid() == True
```

### Implement

```python
# GREEN: Better implementation
def request_password_reset(email):
    user = User.find_by_email(email)
    if not user:
        raise UserNotFound(email)
    
    token = PasswordResetToken.create(user)
    send_reset_email(user.email, token.code)
    
    return ResetResult(success=True)
```

### Test 3: Token Expires

```python
# RED: Expiration behavior
def test_password_reset_token_expires_after_24_hours():
    user = User(email="user@example.com")
    token = PasswordResetToken.create(user)
    
    # Simulate 24 hours passing
    token.created_at = datetime.now() - timedelta(hours=25)
    
    assert token.is_valid() == False
```

### Implement

```python
# GREEN: Add expiration
class PasswordResetToken:
    VALID_FOR_HOURS = 24
    
    def is_valid(self):
        age = datetime.now() - self.created_at
        return age.total_seconds() < (self.VALID_FOR_HOURS * 3600)
```

### Test 4: Prevent Token Reuse

```python
# RED: Security test
def test_cannot_reset_password_twice_with_same_token():
    user = User(email="user@example.com")
    token = PasswordResetToken.create(user)
    
    # First use succeeds
    reset_password(token.code, "new_password")
    assert user.verify_password("new_password") == True
    
    # Second use fails
    with pytest.raises(InvalidToken):
        reset_password(token.code, "another_password")
```

### Final Implementation

```python
def reset_password(token_code, new_password):
    token = PasswordResetToken.find_by_code(token_code)
    
    if not token:
        raise InvalidToken()
    if not token.is_valid():
        raise TokenExpired()
    if token.used:
        raise TokenAlreadyUsed()
    
    user = token.user
    user.set_password(new_password)
    user.save()
    
    token.mark_as_used()
    return PasswordResetResult(success=True)
```

### Test Coverage

This feature has:
- ✅ Happy path (user resets password)
- ✅ Edge cases (token expires, reused token)
- ✅ Error handling (invalid token, missing user)
- ✅ Security (one-time use)

**Coverage: ~95% (exceeds 80% minimum)**

## Common TDD Mistakes to Avoid

### ❌ Mistake 1: Testing Implementation Details

```python
# BAD: Tests the implementation
def test_cache_has_key():
    cache._storage[user_id] = user
    assert user_id in cache._storage

# GOOD: Tests the contract
def test_cache_retrieves_stored_user():
    cache.store(user_id, user)
    retrieved = cache.get(user_id)
    assert retrieved == user
```

### ❌ Mistake 2: Testing Multiple Things at Once

The fields below (`id`, `email`, `password_hash`, `created_at`,
`is_active`) aren't independent behaviors — they're all part of the same
outcome: "creating a user produces a correctly-populated user." That's one
behavior, so it should be one test with one snapshot-style assertion, not
five assertions and definitely not five separate tests.

```python
# BAD: Five assertions for one behavior — if one fails, the failure
# message doesn't tell you which without reading the whole test
def test_user_creation():
    user = User.create(email="test@example.com", password="secret")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.password_hash is not None
    assert user.created_at is not None
    assert user.is_active == True

# GOOD: one behavior, one assertion — the diff on failure shows exactly
# which field(s) were wrong
def test_user_creation_populates_all_fields():
    user = User.create(email="test@example.com", password="secret")
    assert_that(user).matches({
        "id": IsNotNone(),
        "email": "test@example.com",
        "password_hash": IsNotNone(),
        "created_at": IsNotNone(),
        "is_active": True,
    })  # or assert.deepStrictEqual against a fully-specified expected object
```

Splitting into separate tests is correct when the assertions verify
**genuinely independent behaviors** that could reasonably fail for
unrelated reasons — e.g. "creation succeeds with valid input" vs.
"creation rejects a duplicate email" are two different behaviors and
belong in two different tests, each with its own single assertion:

```python
def test_create_succeeds_with_valid_input():
    user = User.create(email="test@example.com", password="secret")
    assert user.id is not None

def test_create_rejects_duplicate_email():
    User.create(email="test@example.com", password="secret")
    with pytest.raises(DuplicateEmailError):
        User.create(email="test@example.com", password="other")
```

### ❌ Mistake 3: Slow Tests

```python
# BAD: Slow, hits real database
def test_user_creation():
    database.connect()  # SLOW!
    user = User.create(email="test@example.com")
    database.disconnect()

# GOOD: Fast, uses mocks
@mock.patch('database.save')
def test_user_creation(mock_save):
    user = User.create(email="test@example.com")
    mock_save.assert_called_once()
```

### ❌ Mistake 4: Skipping Tests

```python
# BAD: Tests that are skipped
@pytest.mark.skip  # Why? This will fail in production!
def test_critical_payment_processing():
    pass

# GOOD: Fix the test or re-evaluate
# If a test is flaky, fix it
# If it's slow, optimize it
# If it's hard to test, refactor the code
```

### ❌ Mistake 5: No Error Case Tests

```python
# BAD: Only happy path
def test_divide():
    assert divide(10, 2) == 5

# GOOD: Happy path + error cases
def test_divide_returns_quotient():
    assert divide(10, 2) == 5

def test_divide_by_zero_raises_error():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_with_negative_numbers():
    assert divide(-10, 2) == -5
```

## Enforcing TDD in Code Review

When reviewing PRs, check:

✅ **Do ALL changes have tests?**
- Tests written first (red-green-refactor cycle)
- Tests cover normal cases AND error cases
- Tests are focused (one behavior per test)

✅ **Is coverage >= 80%?**
- Use coverage tools to verify
- No exceptions (no "emergency low-coverage merges")

✅ **Do tests actually verify behavior?**
- Not just "did the code run"
- But "does it do what it should"

✅ **Are tests clear and maintainable?**
- Anyone can understand what's being tested
- Test names describe the behavior
- Arrange-Act-Assert structure clear

**If any test is missing or coverage is below 80%, request changes.**

## TDD Benefits Summary

| Benefit | Impact |
|---------|--------|
| **Fewer bugs** | Regressions caught by tests before merge |
| **Faster development** | Catch bugs during dev, not in production |
| **Better design** | Code must be testable = clean architecture |
| **Confidence** | Safe refactoring, safe changes |
| **Documentation** | Tests show how code should be used |
| **Team velocity** | Less time debugging, more time building |
| **Legacy code prevention** | Technical debt prevented upfront |

## Implementation Checklist

For every feature:

- [ ] Write test first (RED)
- [ ] Write minimal code to pass (GREEN)
- [ ] Refactor for clarity (REFACTOR)
- [ ] Test error cases
- [ ] Test edge cases
- [ ] Verify coverage >= 80%
- [ ] Tests are fast (<100ms for unit tests)
- [ ] No skipped tests
- [ ] No test implementation details
- [ ] Clear test names describing behavior
- [ ] Arrange-Act-Assert structure

## Configuration Examples

### Python (pytest)

```toml
# pyproject.toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "--cov=src",
    "--cov-fail-under=80",
    "--cov-report=html",
    "--cov-report=term-missing",
    "-v",
]
```

### TypeScript/JavaScript (Jest)

```json
{
  "jest": {
    "collectCoverageFrom": ["src/**/*.{js,ts}"],
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    },
    "testMatch": ["**/__tests__/**/*.(test|spec).[jt]s"]
  }
}
```

### Go

Coverage percentages from `go tool cover` are floats (e.g. `87.5%`), so a
plain `-lt` integer comparison breaks with "integer expression expected".
See `COVERAGE_REQUIREMENTS.md#measuring-coverage` for the working
`bc`-based comparison — that's the canonical version; don't duplicate a
second copy here that can drift out of sync.

## Resources

- [Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) – Kent Beck (the creator)
- [Growing Object-Oriented Software Guided by Tests](https://www.amazon.com/Growing-Object-Oriented-Software-Guided-Tests/dp/0321503627)
- [Clean Code](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882) – Chapter on testing
- [Test Desiderata](https://kentbeck.github.io/TestDesiderata/) – What makes tests good

---

**Last Updated:** 2026-07-11  
**Minimum Coverage Requirement:** 80% (mandatory, not negotiable)  
**See Also:** `patterns/testing/`, `languages/{language}/CONVENTIONS.md`
