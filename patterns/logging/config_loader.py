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


def interpolate_env_vars(value: str) -> str:
    """
    Interpolate environment variables in a string.

    Supports the syntax: ${VAR_NAME} or ${VAR_NAME:-default_value}
    - ${VAR_NAME}: Require the env var to be set; error if missing
    - ${VAR_NAME:-default}: Use default if env var not set

    Args:
        value: String potentially containing env var placeholders

    Returns:
        String with environment variables substituted

    Raises:
        ValueError: If a required env var is not set
    """
    # Pattern: ${VAR_NAME} or ${VAR_NAME:-default_value}
    pattern = r'\$\{([^}:]+)(?::-(.*?))?\}'

    def replace_var(match):
        var_name = match.group(1)
        default_value = match.group(2)

        env_value = os.environ.get(var_name)

        if env_value is not None:
            return env_value

        if default_value is not None:
            return default_value

        # No value and no default — this is an error
        raise ValueError(
            f"Required environment variable '{var_name}' not set and no default provided"
        )

    return re.sub(pattern, replace_var, value)


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


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config_file> [--show-env-vars]", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    show_env_vars = "--show-env-vars" in sys.argv

    try:
        config = load_config(config_file)

        if show_env_vars:
            print("Environment variables used:")
            pattern = r'\$\{([^}:]+)(?::-(.*?))?\}'
            with open(config_file) as f:
                content = f.read()
                matches = re.findall(pattern, content)
                for var_name, default in matches:
                    value = os.environ.get(var_name, default or "(not set)")
                    print(f"  {var_name} = {value}")
            print()

        import json

        print(json.dumps(config, indent=2))
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
