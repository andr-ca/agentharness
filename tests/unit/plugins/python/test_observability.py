"""Unit tests for Python observability and configuration detection."""

from __future__ import annotations

from pathlib import Path

from agentharness.plugins.python.observability import ObservabilityKind, detect_observability
from agentharness.plugins.python.configuration import ConfigKind, detect_configuration

_HERE = Path(__file__).parent.parent.parent.parent
FIXTURES = _HERE / "fixtures" / "python" / "runtime-quality"


class TestObservability:
    def test_no_observability_returns_absent(self) -> None:
        result = detect_observability(FIXTURES / "no-logging")
        assert result.kind == ObservabilityKind.ABSENT


class TestConfiguration:
    def test_no_env_sample_returns_absent(self, tmp_path) -> None:
        result = detect_configuration(tmp_path)
        assert result.kind == ConfigKind.ABSENT

    def test_env_sample_detected(self, tmp_path) -> None:
        (tmp_path / ".env.sample").write_text("KEY=value\n")
        result = detect_configuration(tmp_path)
        assert result.kind == ConfigKind.ENV_SAMPLE
