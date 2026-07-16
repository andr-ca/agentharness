"""Policy fingerprinting — canonical, deterministic hashing of material inputs.

A fingerprint changes whenever any of its declared material inputs changes.
Untracked files, cache directories, and other irrelevant artifacts must not
affect the fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class FingerprintInputs:
    """All material inputs that affect a policy fingerprint.

    profile_content:      The committed policy profile as a JSON string.
    compiler_version:     The version of the compiler producing this fingerprint.
    plugin_versions:      Dict of plugin_id → version for all registered plugins.
    tool_versions:        Dict of tool_name → version for all detected tools.
    dependency_lock_hash: SHA-256 of the project's lock file, or None if absent.
    scope_patterns:       Ordered list of include path patterns from the scope.
    """

    profile_content: str
    compiler_version: str
    plugin_versions: dict[str, str]
    tool_versions: dict[str, str]
    dependency_lock_hash: str | None
    scope_patterns: list[str]


def compute_fingerprint(inputs: FingerprintInputs) -> str:
    """Return the SHA-256 hex fingerprint of *inputs*.

    The fingerprint is deterministic: given the same inputs, this function
    always returns the same value regardless of process, host, or run order.
    """
    canonical = _canonical_json(inputs)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _canonical_json(inputs: FingerprintInputs) -> str:
    """Produce a stable, NUL-free JSON encoding of the inputs."""
    data = {
        "compiler_version": inputs.compiler_version,
        "dependency_lock_hash": inputs.dependency_lock_hash,
        "plugin_versions": dict(sorted(inputs.plugin_versions.items())),
        "profile_content": inputs.profile_content,
        "scope_patterns": sorted(inputs.scope_patterns),
        "tool_versions": dict(sorted(inputs.tool_versions.items())),
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))
