"""Tests for tools/verify-doc-ownership.py."""
import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "verify-doc-ownership.py"
spec = importlib.util.spec_from_file_location("verify_doc_ownership", MODULE_PATH)
vdo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vdo)


def test_load_ownership_map_missing_file_returns_empty(tmp_path):
    assert vdo.load_ownership_map(tmp_path) == []


def test_load_ownership_map_parses_entries(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text(
        "- paths: [\"tools/setup/harness-link.sh\"]\n"
        "  docs: [\"docs/INTEGRATION.md\", \"MANIFEST.md\"]\n"
    )
    entries = vdo.load_ownership_map(tmp_path)
    assert entries == [
        vdo.OwnershipEntry(
            paths=("tools/setup/harness-link.sh",),
            docs=("docs/INTEGRATION.md", "MANIFEST.md"),
        )
    ]


def test_load_ownership_map_empty_file_returns_empty(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("")
    assert vdo.load_ownership_map(tmp_path) == []


def test_load_ownership_map_rejects_malformed_yaml(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("paths: [unterminated\n")
    with pytest.raises(vdo.MapError, match="not valid YAML"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_non_list_top_level(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("paths: [\"x\"]\n")
    with pytest.raises(vdo.MapError, match="must be a list"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_entry_missing_docs(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text("- paths: [\"x\"]\n")
    with pytest.raises(vdo.MapError, match="entry 0"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_empty_docs_list(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text(
        "- paths: [\"x\"]\n  docs: []\n"
    )
    with pytest.raises(vdo.MapError, match="entry 0"):
        vdo.load_ownership_map(tmp_path)
