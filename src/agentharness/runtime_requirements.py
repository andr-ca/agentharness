"""Strict parser for the canonical runtime dependency artifact lock."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PY_YAML_VERSION = "6.0.3"
FASTJSONSCHEMA_VERSION = "2.21.2"
MAX_REQUIREMENTS_BYTES = 1_048_576
DIRECTIVES = ("--no-binary PyYAML", "--only-binary fastjsonschema")


class RuntimeRequirementsError(ValueError):
    """The canonical runtime artifact lock is missing or malformed."""


@dataclass(frozen=True, slots=True)
class LockedRequirement:
    name: str
    version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeRequirements:
    pyyaml: LockedRequirement
    fastjsonschema: LockedRequirement


def _logical_lines(content: str) -> tuple[str, ...]:
    logical: list[str] = []
    continued = ""
    for raw_line in content.splitlines():
        if "\\" in raw_line and not raw_line.endswith(" \\"):
            raise RuntimeRequirementsError("malformed runtime lock continuation")
        if raw_line.endswith(" \\"):
            fragment = raw_line[:-2].strip()
            if not fragment:
                raise RuntimeRequirementsError("empty runtime lock continuation")
            continued += fragment + " "
            continue
        line = continued + raw_line.strip()
        continued = ""
        if line:
            logical.append(line)
    if continued:
        raise RuntimeRequirementsError("dangling runtime lock continuation")
    return tuple(logical)


def load_runtime_requirements(path: Path) -> RuntimeRequirements:
    try:
        with path.open("rb") as source:
            payload = source.read(MAX_REQUIREMENTS_BYTES + 1)
    except OSError as error:
        raise RuntimeRequirementsError(
            f"cannot read runtime requirements: {error}"
        ) from error
    if len(payload) > MAX_REQUIREMENTS_BYTES:
        raise RuntimeRequirementsError("runtime requirements exceed size limit")
    try:
        lines = _logical_lines(payload.decode("utf-8"))
    except UnicodeError as error:
        raise RuntimeRequirementsError(
            f"cannot decode runtime requirements: {error}"
        ) from error

    for directive in DIRECTIVES:
        if lines.count(directive) != 1:
            raise RuntimeRequirementsError(
                f"runtime lock must contain exactly one {directive} directive"
            )

    declaration_pattern = re.compile(
        r"^(PyYAML|fastjsonschema)==([^\s]+) "
        r"--hash=sha256:([0-9a-f]{64})$",
        re.IGNORECASE,
    )
    declarations: list[LockedRequirement] = []
    for line in lines:
        if line in DIRECTIVES:
            continue
        match = declaration_pattern.fullmatch(line)
        if match is None:
            raise RuntimeRequirementsError(
                "unexpected runtime requirement declaration"
            )
        declarations.append(LockedRequirement(*match.groups()))
    if len(declarations) != 2:
        raise RuntimeRequirementsError(
            "runtime lock must contain exactly two requirements"
        )
    found: dict[str, LockedRequirement] = {}
    for declaration in declarations:
        key = declaration.name.lower()
        if key in found:
            raise RuntimeRequirementsError(
                f"duplicate runtime requirement: {declaration.name}"
            )
        found[key] = declaration
    if set(found) != {"pyyaml", "fastjsonschema"}:
        raise RuntimeRequirementsError(
            "runtime lock must contain exactly PyYAML and fastjsonschema"
        )
    pyyaml = found["pyyaml"]
    fastjsonschema = found["fastjsonschema"]
    if pyyaml.version != PY_YAML_VERSION:
        raise RuntimeRequirementsError(
            f"runtime lock must pin PyYAML=={PY_YAML_VERSION}"
        )
    if fastjsonschema.version != FASTJSONSCHEMA_VERSION:
        raise RuntimeRequirementsError(
            "runtime lock must pin "
            f"fastjsonschema=={FASTJSONSCHEMA_VERSION}"
        )
    return RuntimeRequirements(pyyaml=pyyaml, fastjsonschema=fastjsonschema)
