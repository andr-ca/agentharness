from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = ROOT / "templates/bootstrap/verify-runtime.mjs"
MANIFEST = ROOT / "runtime/python-build-standalone.lock.json"


def test_bootstrap_is_dependency_free_and_avoids_external_extractors() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    forbidden = (
        "npm exec",
        "child_process.exec(",
        "tar x",
        'spawn("python3"',
        "pip install",
    )
    assert all(token not in source for token in forbidden)


def test_https_download_hashes_exact_response_chunks_before_resolving() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    download = source[source.index("async function downloadArtifact") :]
    download = download[: download.index("function decodeField")]
    assert all(
        token in download
        for token in (
            "responseHashes",
            "digest.update(chunk)",
            'digest.digest("hex")',
            "artifact response SHA-512 digest mismatch",
        )
    )


def test_cache_archive_is_authenticated_from_a_nofollow_descriptor() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    reader = source[source.index("async function readAuthenticatedArchive") :]
    reader = reader[: reader.index("async function readVerifiedCacheArchive")]
    assert all(
        token in reader
        for token in (
            "fsConstants.O_NOFOLLOW",
            "await handle.stat()",
            "file.isFile()",
            "file.nlink !== 1",
            "0o600",
            "await handle.read(",
        )
    )


def test_bootstrap_has_exact_production_bounds_and_redirect_policy() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert all(
        value in source
        for value in ("268435456", "1073741824", "100000", "4096", "max_redirects: 3")
    )


def test_reviewed_real_archives_match_pins_and_supported_tar_subset() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reviewed = {
        "aarch64-apple-darwin": (24_942_229, 1_642, 9, 106),
        "aarch64-unknown-linux-gnu": (29_134_681, 3_474, 1_048, 106),
        "x86_64-apple-darwin": (24_639_521, 1_639, 9, 106),
        "x86_64-unknown-linux-gnu": (34_075_380, 3_474, 1_048, 106),
    }
    assert set(reviewed) == {runtime["target"] for runtime in manifest["runtimes"]}
    cache = ROOT / ".tool-cache/runtime-artifacts"
    runtime_files = [
        cache / runtime["url"].rsplit("/", 1)[-1] for runtime in manifest["runtimes"]
    ]
    if not cache.exists() or not all(f.exists() for f in runtime_files):
        pytest.skip("offline checkout has no reviewed real-runtime archive cache")
    for runtime in manifest["runtimes"]:
        path = cache / runtime["url"].rsplit("/", 1)[-1]
        assert path.exists()
        payload = path.read_bytes()
        assert (
            hashlib.sha256(payload).hexdigest(),
            hashlib.sha512(payload).hexdigest(),
        ) == (runtime["sha256"], runtime["sha512"])
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            regular = sum(member.isfile() for member in members)
            symlinks = sum(member.issym() for member in members)
            max_path = max(len(member.name.encode()) for member in members)
            assert (len(payload), regular, symlinks, max_path) == reviewed[
                runtime["target"]
            ]
            assert all(member.isfile() or member.issym() for member in members)
            assert not archive.pax_headers


def test_ci_runs_the_bootstrap_contract_for_all_four_pinned_runtimes() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["runtime-bootstrap-exact-four"]
    expected_setup_python = (
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1"
    )
    setup_python = [
        step
        for step in job["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/setup-python@")
    ]
    hook_setup_python = [
        step
        for step in workflow["jobs"]["hook-tests"]["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/setup-python@")
    ]
    assert len(setup_python) == 1
    assert setup_python[0]["uses"] == expected_setup_python
    assert setup_python[0]["with"]["python-version"] == "3.12"
    assert len(hook_setup_python) == 1
    assert hook_setup_python[0]["uses"] == expected_setup_python
    assert hook_setup_python[0]["with"]["python-version"] == "3.12"
    helper_step_index = next(
        index
        for index, step in enumerate(job["steps"])
        if isinstance(step, dict) and "--online-contract" in step.get("run", "")
    )
    assert job["steps"].index(setup_python[0]) < helper_step_index
    entries = job["strategy"]["matrix"]["include"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {
        runtime["target"]: {
            key: runtime[key] for key in ("url", "sha256", "sha512")
        }
        for runtime in manifest["runtimes"]
    }
    assert {
        entry["target"]: {key: entry[key] for key in ("url", "sha256", "sha512")}
        for entry in entries
    } == expected
    commands = "\n".join(
        step.get("run", "") for step in job["steps"] if isinstance(step, dict)
    )
    assert all(
        token in commands
        for token in (
            "curl --proto '=https'",
            "--proto-redir '=https'",
            "RUNTIME_SHA256",
            "RUNTIME_SHA512",
            "--online-contract",
            "verify-runtime.mjs",
            "--verify-only",
        )
    )
