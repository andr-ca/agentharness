---
language: Python
description: Python-specific naming conventions, style, and best practices
applyTo: "*.py"
---

# Python Conventions & Best Practices

Language-specific guidelines for writing idiomatic and maintainable Python code.

## Naming Conventions

### Functions and Variables
- Use `snake_case` for all function and variable names
- Use descriptive names that explain purpose
- Avoid single-letter names (except loop counters `i`, `j` or math variables `x`, `y`)
- Avoid abbreviations

```python
# Good
user_count = 0
def validate_email_address(email):
    pass

# Bad
uc = 0
def validate_email(e):
    pass
```

### Classes
- Use `PascalCase` for all class names
- Use nouns that describe what the class represents

```python
# Good
class UserRepository:
    pass

class EmailValidator:
    pass

# Bad
class user_repository:
    pass

class Validator:  # Too generic
    pass
```

### Constants
- Use `UPPER_SNAKE_CASE` for module-level constants
- Place constants at the top of the module after imports

```python
# Good
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

# Bad
max_retries = 3
default_timeout = 30
```

### Private Members
- Prefix private methods and attributes with single underscore `_`
- Use double underscore `__` only for name mangling (rare, usually avoid)

```python
class User:
    def __init__(self, name):
        self._internal_data = {}  # Private attribute
    
    def _validate_name(self):  # Private method
        pass
    
    def public_method(self):    # Public method
        pass
```

### Exceptions
- Use `PascalCase` with `Error` or `Exception` suffix
- Use specific exception names that describe the error

```python
# Good
class ValidationError(Exception):
    pass

class DatabaseConnectionError(Exception):
    pass

# Bad
class BadThing(Exception):
    pass

class E(Exception):
    pass
```

## File Organization

### Module Structure

```python
"""Module docstring describing purpose."""

# Imports: standard library, then third-party, then local
import os
import sys
from pathlib import Path
from typing import Optional

import requests

from .utils import helper_function

# Module-level constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Module-level variables (minimize use of module-level mutable state)
_cache = {}

# Classes
class MyClass:
    pass

# Module functions
def my_function():
    pass

# if __name__ == '__main__': block
if __name__ == "__main__":
    main()
```

### Imports

- Put all imports at the top of the file
- Use absolute imports, not relative (prefer `from package import module`)
- Group imports: standard library, third-party, local
- One import per line (except `from x import a, b, c` if concise)
- Use explicit imports; avoid `from module import *`

```python
# Good
from pathlib import Path
import json
from typing import Optional, List

import requests
from requests import Session

from .utils import validate_input

# Bad
from pathlib import *
import requests, json
from . import *
```

## Type Hints

- Use type hints for function parameters and return types
- Use type hints for module-level variables and class attributes
- Import from `typing` (Python 3.8) or `collections.abc` as needed
- Use modern syntax when supported (Python 3.9+: `list[str]` vs `List[str]`)

```python
from typing import Optional, List, Dict, Union

# Good (Python 3.9+)
def process_users(users: list[dict]) -> dict[str, int]:
    pass

# Good (Python 3.8+)
def process_users(users: List[Dict]) -> Dict[str, int]:
    pass

# With Optional
def get_user(user_id: int) -> Optional[User]:
    pass

# With Union (or | in Python 3.10+)
def parse_value(value: Union[str, int]) -> str:
    pass

# Union alternative (Python 3.10+)
def parse_value(value: str | int) -> str:
    pass
```

## Docstrings

Follow Google-style docstrings (or whatever the project uses):

```python
def calculate_average(values: list[float]) -> float:
    """Calculate the average of numeric values.
    
    Args:
        values: List of numeric values.
    
    Returns:
        The arithmetic mean of the values.
    
    Raises:
        ValueError: If values list is empty.
    """
    if not values:
        raise ValueError("Cannot calculate average of empty list")
    return sum(values) / len(values)

class UserRepository:
    """Repository for managing user data persistence.
    
    This class handles all database operations for users,
    including CRUD operations and queries.
    
    Attributes:
        connection: Database connection object.
    """
    pass
```

## Code Style

### Line Length
- Aim for 88 characters (Black's default)
- Hard limit at 100 characters in most cases
- Check your project's `pyproject.toml` for configuration

### Whitespace
- Use 4 spaces for indentation (never tabs)
- Use blank lines:
  - 2 blank lines between top-level functions and classes
  - 1 blank line between methods in a class
  - 1 blank line inside functions for logical grouping (sparingly)

```python
def function_one():
    pass


def function_two():
    pass


class MyClass:
    def method_one(self):
        pass
    
    def method_two(self):
        pass
```

### String Quotes
- Use double quotes by default: `"string"`
- Use single quotes when string contains double quotes: `'It\'s here'` → `"It's here"`
- Use triple quotes for docstrings: `"""`
- No need to avoid one type for another (formatter will normalize)

```python
# All fine, formatter will pick one
name = "Alice"
message = "It's working"
description = """
Multi-line
description
"""
```

### Operators and Spacing
- Space around operators: `x = 1`, `x + 1`, `x == 1`
- No space before comma/colon: `func(a, b)` not `func(a , b)`
- Space after comma in sequences: `[1, 2, 3]`

```python
# Good
x = 1 + 2
if x == 5:
    pass

# Bad
x=1+2
if x==5:
    pass
```

## Common Patterns

### Context Managers
Always use context managers for resource management:

```python
# Good: Context manager ensures file is closed
with open('file.txt') as f:
    content = f.read()

# Good: Database transaction
with database.transaction():
    user.save()
    profile.save()
```

### List/Dict Comprehensions
Use comprehensions for concise transformations:

```python
# Good
squared = [x**2 for x in range(10)]
user_names = {u.id: u.name for u in users}

# Also good (if complex, extract to function)
filtered = [x for x in items if x.is_valid()]
```

### F-strings
Use f-strings for string formatting (Python 3.6+):

```python
# Good
name = "Alice"
message = f"Hello {name}!"

# Also okay if no variables
message = "Hello world"

# Bad
message = "Hello {}".format(name)
message = "Hello %s" % name
```

### Type Checking
Use `isinstance()` for type checking, not `type()`:

```python
# Good
if isinstance(value, str):
    pass

if isinstance(container, (list, tuple)):
    pass

# Bad
if type(value) == str:
    pass
```

## Avoid These Pitfalls

### Mutable Default Arguments
```python
# DANGER: Mutable default persists across calls
def append_item(item, container=[]):
    container.append(item)
    return container

# result1 = append_item(1)  # [1]
# result2 = append_item(2)  # [1, 2] - SHARED!

# GOOD: Use None as sentinel
def append_item(item, container=None):
    if container is None:
        container = []
    container.append(item)
    return container
```

### Bare except and Exception
```python
# Bad: Catches everything including KeyboardInterrupt
try:
    do_something()
except:
    pass

# Bad: Too broad
try:
    do_something()
except Exception:
    pass

# Good: Catch specific exception
try:
    do_something()
except ValueError as e:
    handle_error(e)
```

### Using `is` for Value Comparison
```python
# Bad: `is` checks identity, not equality
if user_id is 5:
    pass

# Good: `==` checks value
if user_id == 5:
    pass

# Correct use of `is`: None, True, False
if value is None:
    pass
```

### Global State
```python
# Bad: Global mutable state
_cache = {}
def get_cached(key):
    if key not in _cache:
        _cache[key] = expensive_operation(key)
    return _cache[key]

# Good: Encapsulate in a class
class Cache:
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        if key not in self._cache:
            self._cache[key] = expensive_operation(key)
        return self._cache[key]
```

### Not Using Generators
```python
# Bad: Loads everything into memory
def get_all_users():
    users = []
    for user_id in range(1, 1000000):
        users.append(fetch_user(user_id))
    return users

# Good: Use generator for lazy evaluation
def get_all_users():
    for user_id in range(1, 1000000):
        yield fetch_user(user_id)
```

## Testing

### Test Organization
- Place tests in `tests/` directory (or match project structure)
- Name test files `test_*.py` or `*_test.py`
- Name test functions `test_*`
- Group related tests in test classes (optional but organized)

```python
# tests/test_user_validator.py
import pytest
from src.validators import validate_email

def test_validate_email_with_valid_address():
    assert validate_email("user@example.com") is True

def test_validate_email_with_invalid_address():
    assert validate_email("invalid") is False

def test_validate_email_raises_on_empty():
    with pytest.raises(ValueError):
        validate_email("")
```

### Fixtures and Setup
Use pytest fixtures for test setup:

```python
import pytest

@pytest.fixture
def user():
    return User(name="Alice", email="alice@example.com")

def test_user_creation(user):
    assert user.name == "Alice"

def test_user_email(user):
    assert user.email == "alice@example.com"
```

## Tools & Configuration

### pyproject.toml
Standard location for Python project configuration:

```toml
[project]
name = "my-package"
version = "0.1.0"
requires-python = ">=3.8"

[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
select = ["E", "F", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Common Commands
```bash
# Format with Black or Ruff
black .
ruff format .

# Lint with Ruff
ruff check .
ruff check . --fix

# Type check with mypy
mypy .

# Run tests
pytest
pytest -v
pytest --cov

# Run with uv or Poetry
uv run pytest
poetry run pytest
```

## Version-Specific Features

### Python 3.9+
- `list[str]` instead of `List[str]`
- `dict[str, int]` instead of `Dict[str, int]`
- New flexible function and variable annotation syntax

### Python 3.10+
- `X | Y` instead of `Union[X, Y]`
- `X | None` instead of `Optional[X]`
- `match/case` statements for pattern matching

### Python 3.11+
- `Self` type hint
- Exception groups with `except*`
- Improved error messages

**Always verify your project's minimum Python version before using new features.**

---

**Last Updated:** 2026-07-11  
**See Also:** COPILOT_INSTRUCTIONS.md for AI-specific guidance
