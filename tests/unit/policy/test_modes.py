"""Unit tests for policy mode aggregation (strict, warn, grace)."""

from __future__ import annotations

from agentharness.policy.modes import ModeAggregator, PolicyMode


class TestModeAggregator:
    def test_all_pass_is_pass(self) -> None:
        agg = ModeAggregator()
        agg.record("req.a", PolicyMode.STRICT, passed=True)
        agg.record("req.b", PolicyMode.STRICT, passed=True)
        assert agg.is_gate_passing()

    def test_strict_fail_blocks(self) -> None:
        agg = ModeAggregator()
        agg.record("req.a", PolicyMode.STRICT, passed=False)
        assert not agg.is_gate_passing()

    def test_warn_fail_does_not_block(self) -> None:
        agg = ModeAggregator()
        agg.record("req.a", PolicyMode.WARN, passed=False)
        assert agg.is_gate_passing()

    def test_grace_fail_does_not_block(self) -> None:
        agg = ModeAggregator()
        agg.record("req.a", PolicyMode.GRACE, passed=False)
        assert agg.is_gate_passing()

    def test_mixed_strict_and_warn_blocks_on_strict(self) -> None:
        agg = ModeAggregator()
        agg.record("req.warn", PolicyMode.WARN, passed=False)
        agg.record("req.strict", PolicyMode.STRICT, passed=False)
        assert not agg.is_gate_passing()

    def test_aggregator_reports_all_failures(self) -> None:
        agg = ModeAggregator()
        agg.record("req.a", PolicyMode.STRICT, passed=False)
        agg.record("req.b", PolicyMode.WARN, passed=False)
        failures = agg.get_failures()
        assert "req.a" in failures
        assert "req.b" in failures
