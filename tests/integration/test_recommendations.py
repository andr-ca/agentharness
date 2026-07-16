"""Integration tests for plugin-backed recommendations."""

from __future__ import annotations

from agentharness.plugins.python.recommend import compose_recommendations


class TestRecommendations:
    def test_compose_returns_sorted_list(self) -> None:
        findings = [
            {"id": "b", "summary": "B", "impact": "low", "cost": "low"},
            {"id": "a", "summary": "A", "impact": "high", "cost": "low"},
        ]
        recs = compose_recommendations(findings)
        assert recs[0].id == "a"

    def test_compose_empty_is_stable(self) -> None:
        assert compose_recommendations([]) == []
