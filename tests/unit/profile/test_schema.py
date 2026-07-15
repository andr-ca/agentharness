from __future__ import annotations

import json
from pathlib import Path

import fastjsonschema
import pytest

from agentharness.profile import (
    ProfileError,
    load_local_override_text,
    load_profile_candidate_text,
    load_profile_text,
)

from .test_loader import profile_yaml

SCHEMA_DIR = Path("src/agentharness/schemas")


@pytest.mark.parametrize("name", ["profile-v1.json", "local-override-v1.json"])
def test_committed_schemas_are_valid_json_schema(name: str) -> None:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    fastjsonschema.compile(schema)


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("schema_version: 1", "schema_version: 2", "profile.schema_invalid"),
        ("project:", "unknown: true\nproject:", "profile.schema_invalid"),
        ("mode: strict", "mode: permissive", "profile.schema_invalid"),
        ("gates: [push, ci, completion]", "gates: [deploy]", "profile.schema_invalid"),
    ],
)
def test_schema_failures_have_stable_code(old: str, new: str, code: str) -> None:
    with pytest.raises(ProfileError) as captured:
        load_profile_text(profile_yaml().replace(old, new))
    assert captured.value.code == code


@pytest.mark.parametrize(
    "forbidden",
    [
        "requirements: {}",
        "command: [other]",
        "runtime: {lock: other.lock}",
        "cache: /tmp/cache",
        "minimum_coverage: 1",
        "gates: [ci]",
        "scope: {include: [src/**]}",
        "bootstrap: {mode: warn}",
    ],
)
def test_override_schema_makes_policy_weakening_unrepresentable(forbidden: str) -> None:
    payload = f"schema_version: 1\n{forbidden}\n"
    with pytest.raises(ProfileError) as captured:
        load_local_override_text(payload)
    assert captured.value.code == "override.schema_invalid"


def test_duplicate_requirement_identifier_is_rejected() -> None:
    payload = profile_yaml().replace(
        "  unit_testing:\n",
        "  unit_testing:\n    provider: python\n    enabled: true\n"
        "    gates: [ci]\n  unit_testing:\n",
        1,
    )
    with pytest.raises(ProfileError) as captured:
        load_profile_text(payload)
    assert captured.value.code == "profile.duplicate_key"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("codeowners: ['@maintainers']", "codeowners: []"),
        ("require_codeowner_approval: true", "require_codeowner_approval: false"),
        ("minimum_total_approvals: 1", "minimum_total_approvals: 0"),
        ("require_expiry: true", "require_expiry: false"),
        ("require_reason: true", "require_reason: false"),
    ],
)
def test_requirement_reduction_protection_cannot_be_disabled(
    old: str, new: str
) -> None:
    with pytest.raises(ProfileError) as captured:
        load_profile_text(profile_yaml().replace(old, new))
    expected = (
        "profile.waiver_protection_invalid"
        if old in {"require_expiry: true", "require_reason: true"}
        else "profile.reduction_protection_invalid"
    )
    assert captured.value.code == expected


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("codeowners: ['@maintainers']", "codeowners: []"),
        ("require_codeowner_approval: true", "require_codeowner_approval: false"),
        ("minimum_total_approvals: 1", "minimum_total_approvals: 0"),
        ("require_expiry: true", "require_expiry: false"),
        ("require_reason: true", "require_reason: false"),
    ],
)
def test_candidate_loader_accepts_structural_reduction_proposals(
    old: str, new: str
) -> None:
    candidate = load_profile_candidate_text(profile_yaml().replace(old, new))
    assert candidate.schema_version == 1
