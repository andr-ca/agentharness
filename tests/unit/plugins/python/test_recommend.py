"""Unit tests for recommendation composition."""

from __future__ import annotations

from agentharness.plugins.python.recommend import (
    Cost,
    Impact,
    Recommendation,
    compose_recommendations,
)


class TestComposeRecommendations:
    def test_empty_findings_returns_empty(self) -> None:
        assert compose_recommendations([]) == []

    def test_sorted_by_impact_then_cost_then_id(self) -> None:
        findings = [
            {"id": "b.low", "summary": "Low B", "impact": "low", "cost": "low"},
            {"id": "a.high", "summary": "High A", "impact": "high", "cost": "low"},
            {"id": "c.medium", "summary": "Med C", "impact": "medium", "cost": "medium"},
        ]
        recs = compose_recommendations(findings)
        assert [r.id for r in recs] == ["a.high", "c.medium", "b.low"]

    def test_optional_flag_defaults_true(self) -> None:
        findings = [{"id": "x", "summary": "X", "impact": "low", "cost": "low"}]
        rec = compose_recommendations(findings)[0]
        assert rec.optional is True

    def test_mandatory_recommendation(self) -> None:
        findings = [
            {"id": "y", "summary": "Y", "impact": "high", "cost": "low", "optional": "false"}
        ]
        rec = compose_recommendations(findings)[0]
        assert rec.optional is False

    def test_stable_sort_is_deterministic(self) -> None:
        findings = [
            {"id": "b", "summary": "B", "impact": "medium", "cost": "medium"},
            {"id": "a", "summary": "A", "impact": "medium", "cost": "medium"},
        ]
        r1 = compose_recommendations(findings)
        r2 = compose_recommendations(list(reversed(findings)))
        assert [r.id for r in r1] == [r.id for r in r2]
