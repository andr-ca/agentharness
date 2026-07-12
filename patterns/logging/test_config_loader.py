#!/usr/bin/env python3
"""
Tests for config_loader.py — environment variable interpolation in YAML configs.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# config_loader.py lives alongside this test file, which isn't on sys.path
# when pytest is invoked from the repo root (or anywhere else).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_loader import interpolate_env_vars, load_config, process_config_value  # noqa: E402


class TestInterpolateEnvVars:
    """Tests for direct env var interpolation."""

    def test_simple_substitution(self):
        """${VAR} is replaced with env var value."""
        os.environ["TEST_VAR"] = "hello"
        result = interpolate_env_vars("prefix-${TEST_VAR}-suffix")
        assert result == "prefix-hello-suffix"

    def test_substitution_with_default(self):
        """${VAR:-default} uses default if env var not set."""
        os.environ.pop("MISSING_VAR", None)
        result = interpolate_env_vars("value: ${MISSING_VAR:-fallback}")
        assert result == "value: fallback"

    def test_substitution_prefers_env_var(self):
        """${VAR:-default} uses env var if set, ignoring default."""
        os.environ["TEST_VAR"] = "actual"
        result = interpolate_env_vars("${TEST_VAR:-default}")
        assert result == "actual"

    def test_multiple_substitutions(self):
        """Multiple ${VAR} in one string are all replaced."""
        os.environ["VAR1"] = "a"
        os.environ["VAR2"] = "b"
        result = interpolate_env_vars("${VAR1}/${VAR2}")
        assert result == "a/b"

    def test_missing_required_var_raises_error(self):
        """${VAR} without default raises error if var not set."""
        os.environ.pop("UNDEFINED_VAR", None)
        with pytest.raises(ValueError, match="UNDEFINED_VAR"):
            interpolate_env_vars("${UNDEFINED_VAR}")

    def test_no_substitution_needed(self):
        """Strings without ${...} are returned unchanged."""
        result = interpolate_env_vars("just a string")
        assert result == "just a string"

    def test_default_with_nested_braces(self):
        """A default value may itself contain literal { } without truncating."""
        os.environ.pop("LOG_FILENAME", None)
        result = interpolate_env_vars("${LOG_FILENAME:-app-{date}.log}")
        assert result == "app-{date}.log"

    def test_whole_string_placeholder_coerces_bool(self):
        """A value that IS a single placeholder recovers its native YAML type."""
        os.environ.pop("OTEL_ENABLED", None)
        assert interpolate_env_vars("${OTEL_ENABLED:-false}") is False
        assert interpolate_env_vars("${OTEL_ENABLED:-true}") is True

    def test_whole_string_placeholder_coerces_float(self):
        os.environ.pop("SAMPLING_PROBABILITY", None)
        result = interpolate_env_vars("${SAMPLING_PROBABILITY:-0.1}")
        assert result == 0.1
        assert isinstance(result, float)

    def test_embedded_placeholder_stays_string(self):
        """A placeholder embedded in surrounding text never coerces type."""
        os.environ.pop("PORT", None)
        result = interpolate_env_vars("localhost:${PORT:-4317}")
        assert result == "localhost:4317"
        assert isinstance(result, str)

    def test_env_var_wins_over_default_with_type_coercion(self):
        os.environ["OTEL_ENABLED"] = "true"
        try:
            assert interpolate_env_vars("${OTEL_ENABLED:-false}") is True
        finally:
            del os.environ["OTEL_ENABLED"]


class TestProcessConfigValue:
    """Tests for recursive config processing."""

    def test_string_value(self):
        """String values are interpolated."""
        os.environ["TEST"] = "value"
        result = process_config_value("${TEST}")
        assert result == "value"

    def test_dict_value(self):
        """Dict values are recursively processed."""
        os.environ["KEY"] = "val"
        config = {"nested": {"var": "${KEY}"}}
        result = process_config_value(config)
        assert result == {"nested": {"var": "val"}}

    def test_list_value(self):
        """List values are recursively processed."""
        os.environ["ITEM"] = "x"
        config = ["${ITEM}", "static"]
        result = process_config_value(config)
        assert result == ["x", "static"]

    def test_number_value(self):
        """Numbers pass through unchanged."""
        assert process_config_value(42) == 42
        assert process_config_value(3.14) == 3.14

    def test_boolean_value(self):
        """Booleans pass through unchanged."""
        assert process_config_value(True) is True
        assert process_config_value(False) is False

    def test_none_value(self):
        """None passes through unchanged."""
        assert process_config_value(None) is None

    def test_complex_nested_structure(self):
        """Complex nested structures are fully processed."""
        os.environ["ENV_VAR"] = "production"
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "env": "${ENV_VAR:-dev}",
            },
            "services": [
                {"name": "auth", "env": "${ENV_VAR}"},
                {"name": "api", "port": 8080},
            ],
        }
        result = process_config_value(config)
        assert result["database"]["env"] == "production"
        assert result["services"][0]["env"] == "production"
        assert result["services"][1]["port"] == 8080


class TestLoadConfig:
    """Tests for loading and processing config files."""

    def test_load_yaml_config(self):
        """Can load and process a YAML config file."""
        os.environ["LOG_LEVEL"] = "DEBUG"

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "logging": {
                            "level": "${LOG_LEVEL:-INFO}",
                            "format": "json",
                        }
                    }
                )
            )

            config = load_config(str(config_path))
            assert config["logging"]["level"] == "DEBUG"
            assert config["logging"]["format"] == "json"

    def test_missing_config_file_raises_error(self):
        """FileNotFoundError raised for missing config file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_uses_defaults_when_env_vars_not_set(self):
        """Defaults are used when environment variables aren't set."""
        os.environ.pop("UNDEFINED_VAR", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "setting": "${UNDEFINED_VAR:-default_value}",
                    }
                )
            )

            config = load_config(str(config_path))
            assert config["setting"] == "default_value"

    def test_empty_yaml_file(self):
        """Empty YAML file loads as empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("")

            config = load_config(str(config_path))
            assert config == {}

    def test_shipped_example_loads_with_zero_env_vars(self):
        """logging.yaml.example must load without any environment variables set."""
        example_path = Path(__file__).resolve().parent / "logging.yaml.example"

        env_backup = dict(os.environ)
        os.environ.clear()
        try:
            config = load_config(str(example_path))
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

        backends = config["logging"]["backends"]
        assert backends["otel"]["enabled"] is False
        assert backends["cloud"]["gcp"]["project_id"] == ""
        assert backends["file"]["filename_pattern"] == "app-{date}.log"
        assert config["logging"]["tracing"]["sampler"]["sampling_probability"] == 0.1


class TestRedactSensitive:
    """Tests for CLI output redaction of secret-shaped keys."""

    def test_redacts_known_secret_keys(self):
        from config_loader import _redact_sensitive

        config = {"instrumentation_key": "abc123", "level": "INFO"}
        result = _redact_sensitive(config)
        assert result["instrumentation_key"] == "***REDACTED***"
        assert result["level"] == "INFO"

    def test_does_not_redact_disabled_or_empty_secrets(self):
        from config_loader import _redact_sensitive

        config = {"api_key": "", "token": False}
        result = _redact_sensitive(config)
        assert result["api_key"] == ""
        assert result["token"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
