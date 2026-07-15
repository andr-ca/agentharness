"""Integration tests for base trust verification."""

from __future__ import annotations

from agentharness.policy.integrity import verify_policy_integrity


class TestBaseTrust:
    def test_integrity_check_uses_base_content(self) -> None:
        import hashlib
        base_policy = '{"tier": "production"}'
        base_hash = hashlib.sha256(base_policy.encode()).hexdigest()
        # Head policy is the same → passes
        result = verify_policy_integrity(base_policy, base_hash)
        assert result.is_intact

    def test_tampered_head_policy_fails(self) -> None:
        import hashlib
        base_policy = '{"tier": "production"}'
        base_hash = hashlib.sha256(base_policy.encode()).hexdigest()
        tampered = '{"tier": "prototype"}'
        result = verify_policy_integrity(tampered, base_hash)
        assert not result.is_intact
        assert "mismatch" in result.reason
