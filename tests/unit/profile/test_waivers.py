"""Unit tests for policy waivers."""

from __future__ import annotations

import pytest

from agentharness.profile.waivers import (
    Waiver,
    WaiverError,
    WaiverRegistry,
)


class TestWaiver:
    def test_valid_waiver(self) -> None:
        w = Waiver(
            requirement_id="req.a",
            reason="Legacy system: fix tracked in JIRA-123",
            owner="team@example.com",
        )
        assert w.requirement_id == "req.a"

    def test_empty_reason_raises(self) -> None:
        with pytest.raises(WaiverError, match="reason"):
            Waiver(requirement_id="req.a", reason="", owner="team@example.com")

    def test_empty_owner_raises(self) -> None:
        with pytest.raises(WaiverError, match="owner"):
            Waiver(requirement_id="req.a", reason="some reason", owner="")

    def test_wildcard_requirement_id_raises(self) -> None:
        with pytest.raises(WaiverError, match="wildcard"):
            Waiver(requirement_id="*", reason="skip all", owner="me@example.com")


class TestWaiverRegistry:
    def test_waiver_applies_to_its_requirement(self) -> None:
        registry = WaiverRegistry()
        registry.add(Waiver(
            requirement_id="req.a",
            reason="tracked in JIRA-123",
            owner="team@example.com",
        ))
        assert registry.is_waived("req.a")
        assert not registry.is_waived("req.b")

    def test_empty_registry_waives_nothing(self) -> None:
        assert not WaiverRegistry().is_waived("req.x")

    def test_waiver_is_visible_in_evidence(self) -> None:
        registry = WaiverRegistry()
        w = Waiver(
            requirement_id="req.c",
            reason="tracked",
            owner="eng@example.com",
        )
        registry.add(w)
        waivers = registry.list_waivers()
        assert len(waivers) == 1
        assert waivers[0].requirement_id == "req.c"
