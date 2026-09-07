"""Tests for tools/verify-doc-ownership.py."""
import importlib.util
import subprocess
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


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout


def _init_repo_with_fake_origin_main(tmp_path: Path) -> Path:
    """A repo with a `main` branch (commit A), a fake `origin/main` ref
    pointing at the same commit (no real remote needed), and a checked-out
    `feature` branch ready for the test to add commits to."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("# fixture\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-q", "-m", "initial")
    main_sha = _run_git(repo, "rev-parse", "HEAD").strip()
    _run_git(repo, "update-ref", "refs/remotes/origin/main", main_sha)
    _run_git(repo, "checkout", "-q", "-b", "feature")
    return repo


def _commit_all(repo: Path, message: str, trailer: str | None = None) -> None:
    _run_git(repo, "add", "-A")
    msg = message if trailer is None else f"{message}\n\n{trailer}"
    _run_git(repo, "commit", "-q", "-m", msg)


def test_resolve_merge_base_finds_common_ancestor(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add src.py")
    merge_base = vdo.resolve_merge_base(repo)
    assert merge_base == _run_git(repo, "rev-parse", "main").strip()


def test_resolve_merge_base_raises_when_ref_missing(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("# fixture\n")
    _run_git(repo, "add", "README.md")
    _run_git(repo, "commit", "-q", "-m", "initial")
    with pytest.raises(vdo.MapError, match="merge-base"):
        vdo.resolve_merge_base(repo)


def test_changed_files_lists_paths_since_merge_base(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "add src and docs")
    merge_base = vdo.resolve_merge_base(repo)
    assert set(vdo.changed_files(repo, merge_base)) == {"src.py", "docs.md"}


def test_has_docs_not_needed_trailer_false_by_default(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add src.py")
    merge_base = vdo.resolve_merge_base(repo)
    assert vdo.has_docs_not_needed_trailer(repo, merge_base) is False


def test_has_docs_not_needed_trailer_true_when_present(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "tweak timing", trailer="Docs-not-needed: internal only")
    merge_base = vdo.resolve_merge_base(repo)
    assert vdo.has_docs_not_needed_trailer(repo, merge_base) is True


def _write_map(repo: Path, entries_yaml: str) -> None:
    (repo / "DOC_OWNERSHIP.yaml").write_text(entries_yaml)


def test_check_doc_ownership_passes_when_doc_touched(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "- paths: [\"src.py\"]\n  docs: [\"docs.md\"]\n")
    _commit_all(repo, "seed map")
    (repo / "src.py").write_text("x = 1\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "change src and doc together")
    assert vdo.check_doc_ownership(repo) == []


def test_check_doc_ownership_fails_when_doc_not_touched(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "- paths: [\"src.py\"]\n  docs: [\"docs.md\"]\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "seed map and doc")
    # Advance the fake origin/main past this seed commit so docs.md is NOT
    # part of the branch's own diff -- only src.py (added next) is.
    seed_sha = _run_git(repo, "rev-parse", "HEAD").strip()
    _run_git(repo, "update-ref", "refs/remotes/origin/main", seed_sha)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "change src only")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "src.py" in errors[0]
    assert "docs.md" in errors[0]


def test_check_doc_ownership_fails_on_unmapped_path(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add unmapped src.py")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "src.py" in errors[0]
    assert "no DOC_OWNERSHIP.yaml entry" in errors[0]


def test_check_doc_ownership_trailer_exempts_unsatisfied_mapped_path(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "- paths: [\"src.py\"]\n  docs: [\"docs.md\"]\n")
    (repo / "docs.md").write_text("# doc\n")
    _commit_all(repo, "seed map and doc")
    seed_sha = _run_git(repo, "rev-parse", "HEAD").strip()
    _run_git(repo, "update-ref", "refs/remotes/origin/main", seed_sha)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "tweak", trailer="Docs-not-needed: no behavior change")
    assert vdo.check_doc_ownership(repo) == []


def test_check_doc_ownership_trailer_does_not_exempt_unmapped_path(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add unmapped", trailer="Docs-not-needed: not relevant here")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "no DOC_OWNERSHIP.yaml entry" in errors[0]


def test_check_doc_ownership_ignores_auto_exempt_paths(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "tools" / "tests").mkdir(parents=True)
    (repo / "tools" / "tests" / "fixture.bats").write_text("# test\n")
    _commit_all(repo, "add test-only fixture")
    assert vdo.check_doc_ownership(repo) == []


def test_check_doc_ownership_reports_malformed_map_as_single_error(tmp_path):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    _write_map(repo, "not: [a, list\n")
    _commit_all(repo, "add broken map")
    errors = vdo.check_doc_ownership(repo)
    assert len(errors) == 1
    assert "not valid YAML" in errors[0]


def test_main_returns_zero_on_clean_repo(tmp_path, monkeypatch, capsys):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "README.md").write_text("# fixture\nchanged\n")
    _commit_all(repo, "doc-only change")
    monkeypatch.chdir(repo)
    assert vdo.main() == 0
    assert "passed" in capsys.readouterr().out


def test_main_returns_one_and_prints_errors(tmp_path, monkeypatch, capsys):
    repo = _init_repo_with_fake_origin_main(tmp_path)
    (repo / "src.py").write_text("x = 1\n")
    _commit_all(repo, "add unmapped src.py")
    monkeypatch.chdir(repo)
    assert vdo.main() == 1
    out = capsys.readouterr().out
    assert "src.py" in out
    assert "1 issue(s) found" in out
