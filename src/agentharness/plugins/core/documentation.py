"""Documentation policy plugin for the core bundle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DocStrategy(StrEnum):
    SPHINX = "sphinx"
    MKDOCS = "mkdocs"
    README_ONLY = "readme_only"
    ABSENT = "absent"


@dataclass(frozen=True)
class DocumentationPolicy:
    strategy: DocStrategy
    has_link_check: bool


def detect_documentation_policy(root: Path) -> DocumentationPolicy:
    """Detect documentation strategy and link checking in *root*. Read-only."""
    strategy = DocStrategy.ABSENT
    if (root / "docs" / "conf.py").exists():
        strategy = DocStrategy.SPHINX
    elif (root / "mkdocs.yml").exists() or (root / "mkdocs.yaml").exists():
        strategy = DocStrategy.MKDOCS
    elif (root / "README.md").exists() or (root / "README.rst").exists():
        strategy = DocStrategy.README_ONLY

    # link checker present in CI or as a script
    has_link_check = (
        any((root / ".github" / "workflows").glob("*link*"))
        if (root / ".github" / "workflows").exists()
        else False
    )
    return DocumentationPolicy(strategy=strategy, has_link_check=has_link_check)
