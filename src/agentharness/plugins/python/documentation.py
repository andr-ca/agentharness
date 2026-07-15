"""Python documentation tooling detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DocumentationKind(StrEnum):
    SPHINX = "sphinx"
    MKDOCS = "mkdocs"
    README_ONLY = "readme_only"
    ABSENT = "absent"


@dataclass(frozen=True)
class DocumentationDetection:
    kind: DocumentationKind


def detect_documentation(root: Path) -> DocumentationDetection:
    """Detect documentation tooling in *root*. Read-only."""
    if (root / "docs" / "conf.py").exists():
        return DocumentationDetection(kind=DocumentationKind.SPHINX)
    if (root / "mkdocs.yml").exists() or (root / "mkdocs.yaml").exists():
        return DocumentationDetection(kind=DocumentationKind.MKDOCS)
    if (root / "README.md").exists() or (root / "README.rst").exists():
        return DocumentationDetection(kind=DocumentationKind.README_ONLY)
    return DocumentationDetection(kind=DocumentationKind.ABSENT)
