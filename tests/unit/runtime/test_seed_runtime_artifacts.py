from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
import threading
import urllib.error
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "tools/runtime/seed-runtime-artifacts.py"
WRAPPER = ROOT / "tools/runtime/seed-runtime-artifacts.sh"


def _load_helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_runtime_artifacts", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lock(tmp_path: Path, payloads: dict[str, bytes]) -> Path:
    lock = tmp_path / "requirements-runtime.lock"
    lock.write_text(
        "--no-binary PyYAML\n"
        "--only-binary fastjsonschema\n\n"
        "PyYAML==6.0.3 --hash=sha256:"
        f"{hashlib.sha256(payloads['pyyaml']).hexdigest()}\n"
        "fastjsonschema==2.21.2 "
        f"--hash=sha256:{hashlib.sha256(payloads['fastjsonschema']).hexdigest()}\n",
        encoding="utf-8",
    )
    return lock


def _downloader(
    payloads: dict[str, bytes], calls: list[str]
) -> Callable[[str, Path], None]:
    def download(url: str, destination: Path) -> None:
        calls.append(url)
        key = "pyyaml" if url.endswith("pyyaml-6.0.3.tar.gz") else "fastjsonschema"
        destination.write_bytes(payloads[key])

    return download


def test_seeds_exact_authenticated_artifacts_without_build_execution(
    tmp_path: Path,
) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source archive", "fastjsonschema": b"wheel"}
    calls: list[str] = []
    cache = tmp_path / "cache"

    helper.seed_artifacts(
        cache, _lock(tmp_path, payloads), _downloader(payloads, calls)
    )

    cached = {
        path.name: path.read_bytes() for path in cache.iterdir() if path.is_file()
    }
    assert cached == {
        ".seed-runtime-artifacts.lock": b"",
        "fastjsonschema-2.21.2-py3-none-any.whl": b"wheel",
        "pyyaml-6.0.3.tar.gz": b"source archive",
    }
    assert len(calls) == 2
    assert all(url.startswith("https://files.pythonhosted.org/") for url in calls)


def test_digest_rejection_leaves_clean_cache(tmp_path: Path) -> None:
    helper = _load_helper()
    expected = {"pyyaml": b"good source", "fastjsonschema": b"good wheel"}
    corrupt = dict(expected, pyyaml=b"corrupt")
    cache = tmp_path / "cache"

    with pytest.raises(helper.SeedError, match="digest"):
        helper.seed_artifacts(
            cache, _lock(tmp_path, expected), _downloader(corrupt, [])
        )

    assert [path.name for path in cache.iterdir()] == [
        ".seed-runtime-artifacts.lock"
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda source: source.replace("PyYAML==6.0.3", "PyYAML==0.3"),
        lambda source: source + "PyYAML==6.0.3 --hash=sha256:" + "0" * 64 + "\n",
        lambda source: source.replace(
            "--no-binary PyYAML\n", "--no-binary PyYAML\n--no-binary PyYAML\n"
        ),
    ],
)
def test_seed_rejects_noncanonical_lock_grammar(
    tmp_path: Path, mutation: object
) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"wheel"}
    lock = _lock(tmp_path, payloads)
    mutate = mutation
    assert callable(mutate)
    lock.write_text(mutate(lock.read_text(encoding="utf-8")), encoding="utf-8")

    with pytest.raises(helper.SeedError, match="lock"):
        helper.seed_artifacts(tmp_path / "cache", lock, _downloader(payloads, []))


def test_valid_cache_cleans_stale_aliases_and_is_idempotent(tmp_path: Path) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "pyyaml-6.0.3.tar.gz").write_bytes(payloads["pyyaml"])
    (cache / "PyYAML-6.0.3.tar.gz").write_bytes(b"stale alias")
    (cache / "fastjsonschema-2.21.2-py3-none-any.whl").write_bytes(
        payloads["fastjsonschema"]
    )

    def forbidden_download(url: str, destination: Path) -> None:
        raise AssertionError(
            f"valid cache unexpectedly downloaded {url} to {destination}"
        )

    lock = _lock(tmp_path, payloads)
    helper.seed_artifacts(cache, lock, forbidden_download)
    helper.seed_artifacts(cache, lock, forbidden_download)

    assert not (cache / "PyYAML-6.0.3.tar.gz").exists()
    assert (cache / "pyyaml-6.0.3.tar.gz").read_bytes() == b"source"


def test_interrupted_acquisition_does_not_partially_promote(tmp_path: Path) -> None:
    helper = _load_helper()
    expected = {"pyyaml": b"new source", "fastjsonschema": b"new wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    old = {
        "pyyaml-6.0.3.tar.gz": b"old source",
        "fastjsonschema-2.21.2-py3-none-any.whl": b"old wheel",
    }
    for name, payload in old.items():
        (cache / name).write_bytes(payload)
    calls = 0

    def interrupted(url: str, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("connection interrupted")
        destination.write_bytes(expected["pyyaml"])

    with pytest.raises(helper.SeedError, match="download"):
        helper.seed_artifacts(cache, _lock(tmp_path, expected), interrupted)

    assert {name: (cache / name).read_bytes() for name in old} == old
    assert not tuple(cache.glob("*.part"))


def test_cache_does_not_trust_canonical_symlinks(tmp_path: Path) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    outside = tmp_path / "outside-source"
    outside.write_bytes(payloads["pyyaml"])
    (cache / "pyyaml-6.0.3.tar.gz").symlink_to(outside)
    (cache / "fastjsonschema-2.21.2-py3-none-any.whl").write_bytes(b"wheel")

    with pytest.raises(helper.SeedError, match="cache"):
        helper.seed_artifacts(
            cache, _lock(tmp_path, payloads), _downloader(payloads, [])
        )

    assert outside.read_bytes() == b"source"


def test_oversize_sparse_cache_artifact_is_rejected_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    oversized = cache / "pyyaml-6.0.3.tar.gz"
    with oversized.open("wb") as stream:
        stream.truncate(helper.MAX_ARTIFACT_BYTES + 1)
    (cache / "fastjsonschema-2.21.2-py3-none-any.whl").write_bytes(b"wheel")
    monkeypatch.setattr(
        Path,
        "open",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("oversize artifact must be rejected before open")
        )
        if self == oversized
        else open(self, *args, **kwargs),
    )

    with pytest.raises(helper.SeedError, match="size"):
        helper.seed_artifacts(
            cache, _lock(tmp_path, payloads), _downloader(payloads, [])
        )


def test_case_only_alias_is_normalized_with_atomic_replaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    canonical = cache / "pyyaml-6.0.3.tar.gz"
    alias = cache / "PyYAML-6.0.3.tar.gz"
    canonical.write_bytes(b"source")
    os.link(canonical, alias)
    (cache / "fastjsonschema-2.21.2-py3-none-any.whl").write_bytes(b"wheel")
    inode = canonical.stat().st_ino
    real_replace = helper.os.replace
    replacements: list[tuple[str, str]] = []

    def observe_replace(source: Path, destination: Path) -> None:
        replacements.append((source.name, destination.name))
        real_replace(source, destination)

    monkeypatch.setattr(helper.os, "replace", observe_replace)
    helper.seed_artifacts(
        cache,
        _lock(tmp_path, payloads),
        lambda url, destination: (_ for _ in ()).throw(AssertionError(url)),
    )

    assert len(replacements) == 2
    assert canonical.stat().st_ino == inode
    assert not alias.exists()


def test_case_variant_symlink_alias_cannot_replace_canonical_artifact(
    tmp_path: Path,
) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    canonical = cache / "pyyaml-6.0.3.tar.gz"
    alias = cache / "PyYAML-6.0.3.tar.gz"
    canonical.write_bytes(payloads["pyyaml"])
    alias.symlink_to(canonical.name)
    (cache / "fastjsonschema-2.21.2-py3-none-any.whl").write_bytes(
        payloads["fastjsonschema"]
    )

    def forbidden_download(url: str, destination: Path) -> None:
        raise AssertionError(f"valid cache unexpectedly downloaded {url}")

    lock = _lock(tmp_path, payloads)
    helper.seed_artifacts(cache, lock, forbidden_download)
    helper.seed_artifacts(cache, lock, forbidden_download)

    assert canonical.is_file()
    assert not canonical.is_symlink()
    assert canonical.read_bytes() == b"source"
    assert not alias.exists()


def test_mixed_generation_cache_fails_closed_when_refresh_is_interrupted(
    tmp_path: Path,
) -> None:
    helper = _load_helper()
    payloads = {"pyyaml": b"source", "fastjsonschema": b"new wheel"}
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "pyyaml-6.0.3.tar.gz").write_bytes(b"source")
    wheel = cache / "fastjsonschema-2.21.2-py3-none-any.whl"
    wheel.write_bytes(b"old wheel")

    def interrupted(url: str, destination: Path) -> None:
        raise OSError("offline")

    with pytest.raises(helper.SeedError, match="download"):
        helper.seed_artifacts(cache, _lock(tmp_path, payloads), interrupted)

    assert wheel.read_bytes() == b"old wheel"


def test_portable_shell_wrapper_delegates_without_bash4_features() -> None:
    syntax = subprocess.run(
        ["bash", "--posix", "-n", str(WRAPPER)], capture_output=True, text=True
    )
    assert syntax.returncode == 0, syntax.stderr
    result = subprocess.run(
        ["bash", str(WRAPPER), "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "seed-runtime-artifacts" in result.stdout


def test_default_downloader_streams_fixed_response_without_metadata_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = _load_helper()
    url = "https://files.pythonhosted.org/packages/artifact.whl"

    class Response:
        def __init__(self) -> None:
            self.chunks = iter((b"first", b"second", b""))

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def geturl(self) -> str:
            return url

        def read(self, size: int) -> bytes:
            assert size == helper.CHUNK_BYTES
            return next(self.chunks)

    monkeypatch.setattr(helper, "_open_url", lambda *args, **kwargs: Response())
    destination = tmp_path / "artifact"

    helper._download(url, destination)

    assert destination.read_bytes() == b"firstsecond"


def test_default_downloader_rejects_redirect_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = _load_helper()

    def redirect(*args: object, **kwargs: object) -> object:
        raise urllib.error.HTTPError(
            "https://files.pythonhosted.org/fixed",
            302,
            "Found",
            {"Location": "https://example.invalid/replaced"},  # type: ignore[arg-type]
            None,
        )

    monkeypatch.setattr(helper, "_open_url", redirect)
    destination = tmp_path / "artifact"

    with pytest.raises(helper.SeedError, match="redirect"):
        helper._download("https://files.pythonhosted.org/fixed", destination)

    assert not destination.exists()


def test_redirect_is_rejected_without_contacting_location(tmp_path: Path) -> None:
    helper = _load_helper()
    contacted = {"redirect": 0, "location": 0}

    class LocationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            contacted["location"] += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"unexpected")

        def log_message(self, format: str, *args: object) -> None:
            return None

    location = ThreadingHTTPServer(("127.0.0.1", 0), LocationHandler)
    location_url = f"http://127.0.0.1:{location.server_port}/artifact"

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            contacted["redirect"] += 1
            self.send_response(302)
            self.send_header("Location", location_url)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return None

    redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True)
        for server in (location, redirect)
    ]
    for thread in threads:
        thread.start()
    try:
        with pytest.raises(helper.SeedError, match="redirect"):
            helper._download(
                f"http://127.0.0.1:{redirect.server_port}/start",
                tmp_path / "artifact",
            )
    finally:
        redirect.shutdown()
        location.shutdown()
        redirect.server_close()
        location.server_close()

    assert contacted == {"redirect": 1, "location": 0}


def test_cli_reports_seed_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    helper = _load_helper()
    monkeypatch.setattr(sys, "argv", ["seed-runtime-artifacts"])

    def fail(cache: Path, lock: Path) -> None:
        raise helper.SeedError("controlled failure")

    monkeypatch.setattr(helper, "seed_artifacts", fail)

    assert helper.main() == 1
    assert "controlled failure" in capsys.readouterr().err
