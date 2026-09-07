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


def test_load_ownership_map_rejects_non_list_paths_value(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text(
        "- paths: \"tools/single.py\"\n  docs: [\"doc.md\"]\n"
    )
    with pytest.raises(vdo.MapError, match="entry 0.*'paths' must be a list"):
        vdo.load_ownership_map(tmp_path)


def test_load_ownership_map_rejects_non_list_docs_value(tmp_path):
    (tmp_path / "DOC_OWNERSHIP.yaml").write_text(
        "- paths: [\"x\"]\n  docs: \"doc.md\"\n"
    )
    with pytest.raises(vdo.MapError, match="entry 0.*'docs' must be a list"):
        vdo.load_ownership_map(tmp_path)


@pytest.mark.parametrize(
    "path",
    [
        "tools/tests/harness-lifecycle.bats",
        "tools/tests/helpers/make-runtime-fixtures.py",
        "tests/unit/test_cli.py",
        "docs/INTEGRATION.md",
        "README.md",
        "DOC_OWNERSHIP.yaml",
    ],
)
def test_is_auto_exempt_true_for_test_and_doc_paths(path):
    assert vdo.is_auto_exempt(path) is True


@pytest.mark.parametrize(
    "path",
    ["tools/setup/harness-link.sh", "src/agentharness/cli.py"],
)
def test_is_auto_exempt_false_for_code_paths(path):
    assert vdo.is_auto_exempt(path) is False


def test_required_docs_for_unmapped_path_returns_none():
    entries = [vdo.OwnershipEntry(paths=("tools/setup/*.sh",), docs=("docs/INTEGRATION.md",))]
    assert vdo.required_docs_for("src/other.py", entries) is None


def test_required_docs_for_matches_glob():
    entries = [vdo.OwnershipEntry(paths=("tools/setup/*.sh",), docs=("docs/INTEGRATION.md",))]
    assert vdo.required_docs_for("tools/setup/harness-link.sh", entries) == {"docs/INTEGRATION.md"}


def test_required_docs_for_unions_multiple_matching_entries():
    entries = [
        vdo.OwnershipEntry(paths=("tools/setup/*.sh",), docs=("docs/INTEGRATION.md",)),
        vdo.OwnershipEntry(paths=("tools/setup/harness-link.sh",), docs=("MANIFEST.md",)),
    ]
    result = vdo.required_docs_for("tools/setup/harness-link.sh", entries)
    assert result == {"docs/INTEGRATION.md", "MANIFEST.md"}
