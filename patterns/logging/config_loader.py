#!/usr/bin/env python3
"""
Config loader with environment variable interpolation.

Loads YAML configuration files and interpolates environment variables
using the ${VAR_NAME:-default_value} syntax.

Usage:
    from config_loader import load_config
    config = load_config('config/logging.yaml')

Environment variable substitution:
    ${LOGGING_LEVEL}           → value of LOGGING_LEVEL env var (error if not set)
    ${LOGGING_LEVEL:-INFO}     → value of LOGGING_LEVEL or "INFO" if not set
    ${LOG_PATH:-./logs}        → value of LOG_PATH or "./logs" if not set

Nested braces in a default (e.g. ``${NAME:-app-{date}.log}``) are supported —
the parser tracks brace depth rather than stopping at the first ``}``.

When a YAML value is *exactly one* placeholder (nothing else in the string),
the substituted result is re-parsed as a YAML scalar so booleans and numbers
(``${OTEL_ENABLED:-false}`` → ``False``, not ``"false"``) round-trip to their
native type. Placeholders embedded in a larger string always stay strings.
"""

import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:
    raise ImportError(
        "PyYAML is required for config_loader. Install with: pip install pyyaml"
    ) from e

_PLACEHOLDER_SCAN_RE = re.compile(r'\$\{[A-Za-z_][A-Za-z0-9_]*(?::-|\})')


def _scan_placeholder(value: str, start: int) -> tuple[str, str | None, int]:
    """
    Parse a single ${VAR} / ${VAR:-default} placeholder beginning at
    ``value[start:start+2] == '${'``, tracking brace depth so a default
    value may itself contain literal ``{``/``}`` characters.

    Returns (var_name, default_or_None, index_just_past_the_closing_brace).
    """
    depth = 1
    j = start + 2
    n = len(value)
    while j < n and depth > 0:
        if value[j] == "{":
            depth += 1
        elif value[j] == "}":
            depth -= 1
        j += 1

    if depth != 0:
        raise ValueError(f"Unbalanced '${{' in {value!r}")

    inner = value[start + 2 : j - 1]
    var_name, sep, default_value = inner.partition(":-")
    return var_name, (default_value if sep else None), j


def interpolate_env_vars(value: Any) -> Any:
    """
    Interpolate environment variables in a string.

    Supports the syntax: ${VAR_NAME} or ${VAR_NAME:-default_value}
    - ${VAR_NAME}: Require the env var to be set; error if missing
    - ${VAR_NAME:-default}: Use default if env var not set

    Non-string values pass through unchanged.

    Args:
        value: String potentially containing env var placeholders

    Returns:
        The interpolated value. If the entire input was a single
        placeholder, the result is re-parsed as a YAML scalar (so it may be
        a bool, int, float, or None rather than a string); otherwise a
        string.

    Raises:
        ValueError: If a required env var is not set
    """
    if not isinstance(value, str) or "${" not in value:
        return value

    pieces: list[str] = []
    i, n = 0, len(value)
    placeholder_count = 0

    while i < n:
        if value[i] == "$" and i + 1 < n and value[i + 1] == "{":
            var_name, default_value, end = _scan_placeholder(value, i)
            env_value = os.environ.get(var_name)

            if env_value is not None:
                pieces.append(env_value)
            elif default_value is not None:
                pieces.append(default_value)
            else:
                raise ValueError(
                    f"Required environment variable '{var_name}' not set and no default provided"
                )

            placeholder_count += 1
            i = end
        else:
            pieces.append(value[i])
            i += 1

    result = "".join(pieces)

    # Whole string was exactly one placeholder — recover its native YAML type.
    if placeholder_count == 1 and len(pieces) == 1:
        return yaml.safe_load(result) if result else result

    return result


def process_config_value(value: Any) -> Any:
    """
    Recursively process config values, interpolating environment variables.

    Handles strings, lists, dicts, and nested structures.

    Args:
        value: Config value (can be any YAML type)

    Returns:
        Processed value with env vars interpolated
    """
    if isinstance(value, str):
        return interpolate_env_vars(value)
    elif isinstance(value, dict):
        return {k: process_config_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [process_config_value(item) for item in value]
    else:
        # Numbers, booleans, None — pass through unchanged
        return value


def load_config(config_path: str) -> Any:
    """
    Load YAML configuration file with environment variable interpolation.

    Args:
        config_path: Path to YAML config file

    Returns:
        Parsed configuration with env vars interpolated. Typically a dict,
        but reflects whatever type the YAML document's root actually is
        (list, string, number, etc.) — same as yaml.safe_load.

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValueError: If required env vars are not set
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    # Process all values to interpolate environment variables
    return process_config_value(config)


_SENSITIVE_KEY_RE = re.compile(
    r"(secret|token|password|passwd|api[_-]?key|credential|instrumentation[_-]?key|auth)",
    re.IGNORECASE,
)


def _redact_sensitive(value: Any, key: str | None = None) -> Any:
    """Recursively mask values whose key name looks secret-shaped."""
    if isinstance(value, dict):
        return {k: _redact_sensitive(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_sensitive(item, key) for item in value]
    if key and _SENSITIVE_KEY_RE.search(key) and value not in (None, "", False):
        return "***REDACTED***"
    return value


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config_file> [--show-env-vars] [--no-redact]", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    show_env_vars = "--show-env-vars" in sys.argv
    no_redact = "--no-redact" in sys.argv

    try:
        config = load_config(config_file)

        if show_env_vars:
            # Report which env vars were referenced and whether the
            # environment or the file's own default supplied the value —
            # never print the resolved value itself, since these
            # placeholders are also used for credentials (API keys,
            # instrumentation keys, tokens).
            print("Environment variables referenced:")
            with open(config_file) as f:
                content = f.read()
            seen = set()
            i = 0
            while True:
                idx = content.find("${", i)
                if idx == -1:
                    break
                var_name, default_value, end = _scan_placeholder(content, idx)
                i = end
                if var_name in seen:
                    continue
                seen.add(var_name)
                source = "environment" if var_name in os.environ else "default"
                print(f"  {var_name} (from {source})")
            print()

        import json

        to_print = config if no_redact else _redact_sensitive(config)
        print(json.dumps(to_print, indent=2, default=str))
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
