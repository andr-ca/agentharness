"""Unit tests for Python configuration detection."""

from __future__ import annotations

from agentharness.plugins.python.configuration import ConfigKind, detect_configuration


class TestConfiguration:
    def test_no_env_returns_absent(self, tmp_path) -> None:
        assert detect_configuration(tmp_path).kind == ConfigKind.ABSENT

    def test_env_sample_detected(self, tmp_path) -> None:
        (tmp_path / ".env.sample").write_text("KEY=\n")
        assert detect_configuration(tmp_path).kind == ConfigKind.ENV_SAMPLE

    def test_env_example_also_detected(self, tmp_path) -> None:
        (tmp_path / ".env.example").write_text("KEY=\n")
        assert detect_configuration(tmp_path).kind == ConfigKind.ENV_SAMPLE
