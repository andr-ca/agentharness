"""Material inputs for Python plugin findings.

Records every file and configuration that contributed to a finding,
enabling the bootstrap system to detect when evidence has become stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MaterialInput:
    """A single file that contributed to a finding.

    path:     project-relative path to the input file.
    sha256:   hex-encoded SHA-256 of the file's contents at detection time.
              Used to detect staleness without re-reading the file.
    """

    path: str
    sha256: str


def collect_inputs(root: Path, relative_paths: list[str]) -> list[MaterialInput]:
    """Collect and hash the named files relative to *root*.

    Skips files that do not exist.  Returns an empty list if none do.
    This function is read-only.
    """
    import hashlib

    inputs = []
    for rel in relative_paths:
        p = root / rel
        if not p.is_file():
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        inputs.append(MaterialInput(path=rel, sha256=digest))
    return inputs
