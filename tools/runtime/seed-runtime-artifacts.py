#!/usr/bin/env python3
"""Acquire runtime build inputs as authenticated bytes without executing them."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import stat
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import IO, BinaryIO, NamedTuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agentharness.runtime_requirements import (  # noqa: E402
    RuntimeRequirementsError,
    load_runtime_requirements,
)

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


class SeedError(RuntimeError):
    """The authenticated artifact cache could not be prepared."""


class Artifact(NamedTuple):
    package: str
    filename: str
    url: str
    aliases: tuple[str, ...]


ARTIFACTS = (
    Artifact(
        "PyYAML",
        "pyyaml-6.0.3.tar.gz",
        "https://files.pythonhosted.org/packages/05/8e/"
        "961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/"
        "pyyaml-6.0.3.tar.gz",
        ("pyyaml-6.0.3.tar.gz", "PyYAML-6.0.3.tar.gz"),
    ),
    Artifact(
        "fastjsonschema",
        "fastjsonschema-2.21.2-py3-none-any.whl",
        "https://files.pythonhosted.org/packages/cb/a8/"
        "20d0723294217e47de6d9e2e40fd4a9d2f7c4b6ef974babd482a59743694/"
        "fastjsonschema-2.21.2-py3-none-any.whl",
        ("fastjsonschema-2.21.2-py3-none-any.whl",),
    ),
)

Downloader = Callable[[str, Path], None]


def _expected(lock: Path) -> dict[str, str]:
    try:
        requirements = load_runtime_requirements(lock)
    except RuntimeRequirementsError as error:
        raise SeedError(f"canonical runtime lock is invalid: {error}") from error
    locked = {
        "pyyaml": requirements.pyyaml,
        "fastjsonschema": requirements.fastjsonschema,
    }
    expected: dict[str, str] = {}
    for artifact in ARTIFACTS:
        requirement = locked[artifact.package.lower()]
        version_marker = f"-{requirement.version}"
        if version_marker not in artifact.filename or not artifact.url.endswith(
            artifact.filename
        ):
            raise SeedError(
                f"fixed {artifact.package} artifact identity disagrees "
                "with canonical lock"
            )
        expected[artifact.filename] = requirement.sha256
    return expected


def _digest(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise SeedError(f"cannot stat cached artifact: {error}") from error
    if size > MAX_ARTIFACT_BYTES:
        raise SeedError("cached artifact exceeds size limit")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            total += len(chunk)
            if total > MAX_ARTIFACT_BYTES:
                raise SeedError("cached artifact exceeds size limit")
            digest.update(chunk)
    return digest.hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: IO[bytes],
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> None:
        return None


_URL_OPENER = urllib.request.build_opener(_NoRedirect())


def _open_url(request: urllib.request.Request, timeout: int) -> BinaryIO:
    return _URL_OPENER.open(request, timeout=timeout)  # type: ignore[no-any-return]


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "agentharness/0.2"})
    try:
        with _open_url(request, timeout=30) as response:
            _stream_response(response, destination)
    except urllib.error.HTTPError as error:
        if 300 <= error.code < 400:
            raise SeedError("artifact redirect rejected") from error
        raise SeedError(f"artifact download failed: {error}") from error
    except SeedError:
        raise
    except (OSError, ValueError) as error:
        raise SeedError(f"artifact download failed: {error}") from error


def _stream_response(response: BinaryIO, destination: Path) -> None:
    total = 0
    with destination.open("xb") as output:
        while chunk := response.read(CHUNK_BYTES):
            total += len(chunk)
            if total > MAX_ARTIFACT_BYTES:
                raise SeedError("artifact download exceeds byte limit")
            output.write(chunk)
        output.flush()
        os.fsync(output.fileno())


def _cache_is_valid(cache: Path, expected: dict[str, str]) -> bool:
    return all(
        (path := cache / filename).is_file() and _digest(path) == digest
        for filename, digest in expected.items()
    )


def _validate_canonical_types(cache: Path) -> None:
    for artifact in ARTIFACTS:
        path = cache / artifact.filename
        if path.exists() or path.is_symlink():
            if not stat.S_ISREG(path.lstat().st_mode):
                raise SeedError(
                    f"cache artifact is not a regular file: {artifact.filename}"
                )


def _remove_aliases(cache: Path) -> None:
    canonical = {
        artifact.filename.lower(): cache / artifact.filename
        for artifact in ARTIFACTS
    }
    aliases = {
        alias.lower() for artifact in ARTIFACTS for alias in artifact.aliases
    }
    for path in tuple(cache.iterdir()):
        normalized = path.name.lower()
        canonical_path = canonical.get(normalized)
        if (
            normalized in aliases
            and canonical_path is not None
            and path.name != canonical_path.name
        ):
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                path.unlink()
                continue
            if not stat.S_ISREG(mode):
                raise SeedError(f"artifact alias is not a regular file: {path.name}")
            if canonical_path.exists() and os.path.samefile(path, canonical_path):
                temporary = cache / f".case-normalize-{canonical_path.name}"
                os.replace(path, temporary)
                os.replace(temporary, canonical_path)
            else:
                path.unlink()


def seed_artifacts(
    cache: Path, lock: Path, downloader: Downloader = _download
) -> None:
    """Prepare exactly one canonical authenticated artifact for each package."""
    expected = _expected(lock)
    cache.mkdir(parents=True, exist_ok=True)
    lock_path = cache / ".seed-runtime-artifacts.lock"
    try:
        with lock_path.open("a+b") as lock_stream:
            fcntl.flock(lock_stream, fcntl.LOCK_EX)
            _validate_canonical_types(cache)
            if _cache_is_valid(cache, expected):
                _remove_aliases(cache)
                _validate_canonical_types(cache)
                if _cache_is_valid(cache, expected):
                    return
            with tempfile.TemporaryDirectory(prefix=".seed-", dir=cache) as temporary:
                staging = Path(temporary)
                for artifact in ARTIFACTS:
                    destination = staging / artifact.filename
                    try:
                        downloader(artifact.url, destination)
                    except SeedError:
                        raise
                    except Exception as error:
                        raise SeedError(f"artifact download failed: {error}") from error
                    if _digest(destination) != expected[artifact.filename]:
                        raise SeedError(
                            f"{artifact.package} artifact digest does not match "
                            "canonical lock"
                        )
                for artifact in ARTIFACTS:
                    os.replace(staging / artifact.filename, cache / artifact.filename)
                _remove_aliases(cache)
                _validate_canonical_types(cache)
                if not _cache_is_valid(cache, expected):
                    raise SeedError("runtime artifact cache is a mixed generation")
    except SeedError:
        raise
    except OSError as error:
        raise SeedError(f"cannot prepare runtime artifact cache: {error}") from error


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed-runtime-artifacts",
        description=(
            "Download fixed runtime build artifacts and verify canonical hashes."
        ),
    )
    parser.add_argument(
        "cache",
        nargs="?",
        type=Path,
        default=ROOT / ".tool-cache/runtime-artifacts",
    )
    parser.add_argument(
        "--lock", type=Path, default=ROOT / "requirements-runtime.lock"
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    try:
        seed_artifacts(args.cache, args.lock)
    except SeedError as error:
        print(f"runtime artifact seed failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
