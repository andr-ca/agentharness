"""CI gate — validate CI event context and policy integrity."""

from __future__ import annotations

from agentharness.gates.context import CIContext


def read_ci_context(
    event_name: str,
    head_sha: str,
    ref: str,
    base_sha: str | None = None,
) -> CIContext:
    """Construct a CIContext from GitHub Actions environment values."""
    return CIContext(
        event_name=event_name,
        base_sha=base_sha,
        head_sha=head_sha,
        ref=ref,
    )
