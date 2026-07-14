#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import http.server
import io
import json
import shutil
import ssl
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / ".tool-cache/runtime-bootstrap-fixtures"
RUNTIME_MANIFEST = ROOT / "runtime/python-build-standalone.lock.json"
IDENTITY = {
    "bundled_plugins": {},
    "compatibility_provider_version": "0.1.0",
    "core_version": "0.1.0",
    "schema_version": 1,
}
TARGETS = (
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
)


def zipapp(identity: dict[str, object] = IDENTITY) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo(
            "agentharness-runtime-identity.json", (1980, 1, 1, 0, 0, 0)
        )
        archive.writestr(
            info, json.dumps(identity, sort_keys=True, separators=(",", ":"))
        )
        launch = zipfile.ZipInfo("__main__.py", (1980, 1, 1, 0, 0, 0))
        archive.writestr(launch, "print('fixture')\n")
    return stream.getvalue()


def member(
    name: str, payload: bytes = b"", type_: bytes = tarfile.REGTYPE, link: str = ""
) -> tarfile.TarInfo:
    item = tarfile.TarInfo(name)
    item.type = type_
    item.linkname = link
    item.size = len(payload) if type_ in {tarfile.REGTYPE, tarfile.AREGTYPE} else 0
    item.mode = (
        0o755 if type_ == tarfile.DIRTYPE or name.startswith("python/bin/") else 0o644
    )
    item.mtime = 0
    return item


def archive(
    entries: list[tuple[tarfile.TarInfo, bytes]], *, fmt: int = tarfile.USTAR_FORMAT
) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=fmt) as output:
        for item, payload in entries:
            output.addfile(item, io.BytesIO(payload) if item.isfile() else None)
    return gzip.compress(stream.getvalue(), mtime=0)


def valid_runtime() -> bytes:
    interpreter = (
        b"#!/bin/sh\n"
        b'printf \'%s\\n\' "$*" >> "$AGENTHARNESS_FIXTURE_LAUNCH_LOG"\n'
        b"exit 0\n"
    )
    return archive(
        [
            (member("python", type_=tarfile.DIRTYPE), b""),
            (member("python/bin", type_=tarfile.DIRTYPE), b""),
            (member("python/lib", type_=tarfile.DIRTYPE), b""),
            (member("python/bin/python3.12", interpreter), interpreter),
            (
                member("python/bin/python3", type_=tarfile.SYMTYPE, link="python3.12"),
                b"",
            ),
            (
                member(
                    "python/bin/python-copy",
                    type_=tarfile.LNKTYPE,
                    link="python/bin/python3.12",
                ),
                b"",
            ),
            (member("python/lib/marker", b"runtime"), b"runtime"),
        ]
    )


def runtime_with_entrypoint(*, mode: int = 0o755, directory: bool = False) -> bytes:
    if directory:
        return archive(
            [
                (member("python", type_=tarfile.DIRTYPE), b""),
                (member("python/bin", type_=tarfile.DIRTYPE), b""),
                (member("python/bin/python3", type_=tarfile.DIRTYPE), b""),
            ]
        )
    payload = b"#!/bin/sh\nexit 0\n"
    item = member("python/bin/python3", payload)
    item.mode = mode
    return archive([(item, payload)])


def swapping_runtime() -> bytes:
    payload = (
        b"#!/bin/sh\n"
        b"printf 'MALICIOUS\\n' >> \"$AGENTHARNESS_FIXTURE_LAUNCH_LOG\"\n"
        b"exit 0\n"
    )
    return archive([(member("python/bin/python3", payload), payload)])


def valid_npm(
    payload: bytes,
    package_identity: dict[str, str] | None = None,
) -> bytes:
    package = json.dumps(
        package_identity
        if package_identity is not None
        else {"name": "agentharness-toolkit", "version": "0.2.0"},
        separators=(",", ":"),
    ).encode()
    return archive(
        [
            (member("package/package.json", package), package),
            (member("package/dist/agentharness.pyz", payload), payload),
        ]
    )


def raw_mutation(payload: bytes, mutate: Callable[[bytearray], None]) -> bytes:
    raw = bytearray(gzip.decompress(payload))
    mutate(raw)
    return gzip.compress(bytes(raw), mtime=0)


def lock_document(
    npm: bytes, runtime: bytes, pyz: bytes, *, identity: dict[str, object] = IDENTITY
) -> dict[str, object]:
    runtime_items = []
    for target in TARGETS:
        filename = f"cpython-3.12.13%2B20260510-{target}-install_only_stripped.tar.gz"
        runtime_items.append(
            {
                "target": target,
                "url": "https://github.com/astral-sh/python-build-standalone/releases/download/20260510/"
                + filename,
                "sha256": hashlib.sha256(runtime).hexdigest(),
                "sha512": hashlib.sha512(runtime).hexdigest(),
                "archive_prefix": "python/",
                "interpreter_path": "python/bin/python3",
            }
        )
    npm_sha = hashlib.sha512(npm).digest()
    return {
        "schema_version": 1,
        "package": {
            "name": "agentharness-toolkit",
            "version": "0.2.0",
            "registry_url": "https://registry.npmjs.org",
            "tarball_url": "https://registry.npmjs.org/agentharness-toolkit/-/agentharness-toolkit-0.2.0.tgz",
            "registry_sri": "sha512-" + base64.b64encode(npm_sha).decode(),
            "sha512": npm_sha.hex(),
            "allowed_mirror_url": "https://artifacts.example.test/agentharness.tgz",
        },
        "zipapp": {
            "path": "package/dist/agentharness.pyz",
            "sha512": hashlib.sha512(pyz).hexdigest(),
            **identity,
        },
        "runtimes": runtime_items,
        "acquisition": {
            "selected_target": TARGETS[0],
            "selected_source": "upstream",
            "mirror_policy": {
                "require_https": True,
                "require_matching_digest": True,
                "allowed_runtime_mirror_hosts": ["artifacts.example.test"],
            },
            "limits": {
                "max_compressed_bytes": 268435456,
                "max_expanded_bytes": 1073741824,
                "max_member_bytes": 268435456,
                "max_members": 100000,
                "max_redirects": 3,
                "max_path_bytes": 4096,
            },
            "bootstrap_protocol_version": 1,
        },
    }


def write_case(
    name: str,
    runtime: bytes,
    npm: bytes,
    pyz: bytes,
    lock: dict[str, object] | None = None,
) -> None:
    directory = OUTPUT / name
    directory.mkdir(parents=True)
    (directory / "runtime.tar.gz").write_bytes(runtime)
    (directory / "npm.tgz").write_bytes(npm)
    document = lock if lock is not None else lock_document(npm, runtime, pyz)
    (directory / "runtime.lock.json").write_text(
        json.dumps(document, sort_keys=True), encoding="utf-8"
    )


def main() -> int:
    shutil.rmtree(OUTPUT, ignore_errors=True)
    OUTPUT.mkdir(parents=True)
    pyz = zipapp()
    runtime = valid_runtime()
    npm = valid_npm(pyz)
    write_case("valid", runtime, npm, pyz)
    (OUTPUT / "valid" / "malicious-runtime.tar.gz").write_bytes(swapping_runtime())

    hostile: dict[str, bytes] = {
        "absolute": archive([(member(str(OUTPUT / "outside-sentinel"), b"x"), b"x")]),
        "traversal": archive([(member("python/../../outside", b"x"), b"x")]),
        "drive": archive([(member("C:/outside", b"x"), b"x")]),
        "unc": archive([(member("\\\\server\\share", b"x"), b"x")]),
        "escaping-link": archive(
            [
                (
                    member(
                        "python/bin/python3",
                        type_=tarfile.SYMTYPE,
                        link="../../../outside",
                    ),
                    b"",
                )
            ]
        ),
        "dangling-link": archive(
            [(member("python/bin/python3", type_=tarfile.SYMTYPE, link="missing"), b"")]
        ),
        "cyclic-link": archive(
            [
                (member("python/bin/python3", type_=tarfile.SYMTYPE, link="a"), b""),
                (member("python/bin/a", type_=tarfile.SYMTYPE, link="python3"), b""),
            ]
        ),
        "deep-link": archive(
            [
                (
                    member(f"python/bin/l{i}", type_=tarfile.SYMTYPE, link=f"l{i + 1}"),
                    b"",
                )
                for i in range(10)
            ]
            + [
                (member("python/bin/l10", b"x"), b"x"),
                (member("python/bin/python3", type_=tarfile.SYMTYPE, link="l0"), b""),
            ]
        ),
        "hardlink-directory": archive(
            [
                (member("python/dir", type_=tarfile.DIRTYPE), b""),
                (
                    member(
                        "python/bin/python3",
                        type_=tarfile.LNKTYPE,
                        link="python/dir",
                    ),
                    b"",
                ),
            ]
        ),
        "entrypoint-directory": runtime_with_entrypoint(directory=True),
        "entrypoint-non-executable": runtime_with_entrypoint(mode=0o644),
        "fifo": archive([(member("python/bin/python3", type_=tarfile.FIFOTYPE), b"")]),
        "device": archive([(member("python/bin/python3", type_=tarfile.CHRTYPE), b"")]),
        "unknown-type": archive([(member("python/bin/python3", type_=b"Z"), b"")]),
        "duplicate": archive(
            [
                (member("python/bin/python3", b"a"), b"a"),
                (member("python/bin/python3", b"b"), b"b"),
            ]
        ),
        "collision": archive(
            [
                (member("python/bin", b"a"), b"a"),
                (member("python/bin/python3", b"b"), b"b"),
            ]
        ),
        "unexpected-layout": archive([(member("other/bin/python3", b"x"), b"x")]),
        "cross-artifact": archive(
            [(member("package/dist/agentharness.pyz", pyz), pyz)]
        ),
        "member-limit": archive(
            [(member("python/bin/python3", b"x" * 4096), b"x" * 4096)]
        ),
        "expanded-limit": archive(
            [(member(f"python/f{i}", b"x" * 1024), b"x" * 1024) for i in range(5)]
        ),
        "count-limit": archive(
            [(member(f"python/f{i}", b"x"), b"x") for i in range(12)]
        ),
        "path-limit": archive(
            [(member("python/" + "a" * 80 + "/" + "b" * 80, b"x"), b"x")]
        ),
    }
    hostile["gnu-longname"] = archive(
        [(member("python/" + "a" * 150, b"x"), b"x")], fmt=tarfile.GNU_FORMAT
    )
    hostile["gnu-longlink"] = archive(
        [(member("python/bin/python3", type_=tarfile.SYMTYPE, link="a" * 150), b"")],
        fmt=tarfile.GNU_FORMAT,
    )
    valid_pax = member("placeholder", b"pax")
    valid_pax.pax_headers = {"path": "python/lib/pax-marker", "size": "3"}
    valid_pax_runtime = archive(
        [
            (
                member("python/bin/python3.12", b"#!/bin/sh\nexit 0\n"),
                b"#!/bin/sh\nexit 0\n",
            ),
            (
                member("python/bin/python3", type_=tarfile.SYMTYPE, link="python3.12"),
                b"",
            ),
            (valid_pax, b"pax"),
        ],
        fmt=tarfile.PAX_FORMAT,
    )
    pax_item = member("python/bin/python3", b"x")
    pax_item.pax_headers = {"comment": "forbidden"}
    hostile["pax-metadata"] = archive([(pax_item, b"x")], fmt=tarfile.PAX_FORMAT)
    global_stream = io.BytesIO()
    with tarfile.open(
        fileobj=global_stream,
        mode="w",
        format=tarfile.PAX_FORMAT,
        pax_headers={"comment": "forbidden"},
    ) as output:
        output.addfile(member("python/bin/python3", b"x"), io.BytesIO(b"x"))
    hostile["global-pax"] = gzip.compress(global_stream.getvalue(), mtime=0)
    nul_pax = member("placeholder", b"x")
    nul_pax.pax_headers = {"path": "python/\0outside"}
    hostile["nul-path"] = archive([(nul_pax, b"x")], fmt=tarfile.PAX_FORMAT)
    invalid_pax = member("placeholder", b"x")
    invalid_pax.pax_headers = {"size": "not-a-number"}
    hostile["invalid-pax"] = archive([(invalid_pax, b"x")], fmt=tarfile.PAX_FORMAT)
    hostile["invalid-checksum"] = raw_mutation(
        runtime, lambda raw: raw.__setitem__(0, raw[0] ^ 1)
    )
    hostile["invalid-numeric"] = raw_mutation(
        runtime, lambda raw: raw.__setitem__(slice(124, 136), b"zzzzzzzzzzzz")
    )
    hostile["invalid-utf8"] = raw_mutation(
        runtime, lambda raw: raw.__setitem__(0, 0xFF)
    )
    hostile["truncated-header"] = gzip.compress(gzip.decompress(runtime)[:300], mtime=0)
    hostile["truncated-data"] = gzip.compress(gzip.decompress(runtime)[:700], mtime=0)
    hostile["trailing-data"] = gzip.compress(
        gzip.decompress(runtime) + b"nonzero trailing bytes", mtime=0
    )

    for name, bad_runtime in hostile.items():
        write_case(name, bad_runtime, npm, pyz)
    write_case("valid-pax", valid_pax_runtime, npm, pyz)

    wrong_npm_lock = lock_document(npm, runtime, pyz)
    wrong_npm_lock["package"]["sha512"] = "00" * 64  # type: ignore[index]
    write_case("wrong-npm-digest", runtime, npm, pyz, wrong_npm_lock)
    wrong_runtime_lock = lock_document(npm, runtime, pyz)
    wrong_runtime_lock["runtimes"][0]["sha512"] = "00" * 64  # type: ignore[index]
    write_case("wrong-runtime-digest", runtime, npm, pyz, wrong_runtime_lock)
    identity_mutations = {
        "identity-mismatch": {**IDENTITY, "core_version": "9.9.9"},
        "schema-identity-mismatch": {**IDENTITY, "schema_version": 2},
        "plugin-identity-mismatch": {
            **IDENTITY,
            "bundled_plugins": {"unexpected": "1.0.0"},
        },
        "provider-identity-mismatch": {
            **IDENTITY,
            "compatibility_provider_version": "9.9.9",
        },
    }
    for case_name, bad_identity in identity_mutations.items():
        bad_pyz = zipapp(bad_identity)
        bad_npm = valid_npm(bad_pyz)
        bad_identity_lock = lock_document(bad_npm, runtime, bad_pyz)
        zipapp_lock = bad_identity_lock["zipapp"]
        if not isinstance(zipapp_lock, dict):
            raise TypeError("fixture zipapp lock must be an object")
        zipapp_lock.update(IDENTITY)
        write_case(case_name, runtime, bad_npm, bad_pyz, bad_identity_lock)
    bad_package_npm = valid_npm(
        pyz,
        {"name": "different-package", "version": "0.2.0"},
    )
    write_case(
        "package-identity-mismatch",
        runtime,
        bad_package_npm,
        pyz,
        lock_document(bad_package_npm, runtime, pyz),
    )
    schema_lock = lock_document(npm, runtime, pyz)
    schema_lock["schema_version"] = 2
    write_case("schema-mismatch", runtime, npm, pyz, schema_lock)
    duplicate = OUTPUT / "duplicate-lock"
    duplicate.mkdir()
    (duplicate / "runtime.tar.gz").write_bytes(runtime)
    (duplicate / "npm.tgz").write_bytes(npm)
    serialized = json.dumps(lock_document(npm, runtime, pyz), sort_keys=True)
    (duplicate / "runtime.lock.json").write_text(
        serialized.replace('{"acquisition"', '{"schema_version":1,"acquisition"', 1),
        encoding="utf-8",
    )
    duplicate_control = OUTPUT / "duplicate-control-lock"
    duplicate_control.mkdir()
    (duplicate_control / "runtime.tar.gz").write_bytes(runtime)
    (duplicate_control / "npm.tgz").write_bytes(npm)
    (duplicate_control / "runtime.lock.json").write_text(
        '{"bad\\u001b[31m":1,"bad\\u001b[31m":2}', encoding="utf-8"
    )
    manifest = {
        "cases": sorted(path.name for path in OUTPUT.iterdir()),
        "hostile_archives": sorted(hostile),
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    return 0


def serve_fixtures(
    fixture_root: Path,
    port_file: Path,
    certificate: Path,
    private_key: Path,
) -> int:
    class FixtureHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/npm":
                self.send_file(fixture_root / "valid/npm.tgz")
                return
            if self.path == "/runtime":
                self.send_file(fixture_root / "valid/runtime.tar.gz")
                return
            if self.path == "/redirect-npm":
                self.send_response(302)
                self.send_header("Location", "/npm")
                self.end_headers()
                return
            if self.path.startswith("/redirect-loop/"):
                count = int(self.path.rsplit("/", 1)[-1])
                self.send_response(302)
                self.send_header("Location", f"/redirect-loop/{count + 1}")
                self.end_headers()
                return
            if self.path == "/redirect-http":
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1/forbidden")
                self.end_headers()
                return
            if self.path == "/redirect-unapproved":
                self.send_response(302)
                self.send_header("Location", "https://example.com/forbidden")
                self.end_headers()
                return
            if self.path == "/partial":
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.write(b"partial")
                self.close_connection = True
                return
            self.send_error(404)

        def send_file(self, path: Path) -> None:
            payload = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format_: str, *args: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, private_key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    port_file.write_text(str(server.server_port), encoding="ascii")
    server.serve_forever()
    return 0


def write_online_contract(runtime_archive: Path, target: str, output: Path) -> int:
    manifest = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    runtimes = manifest.get("runtimes")
    if not isinstance(runtimes, list):
        raise ValueError("runtime manifest must contain a runtime list")
    selected = next(
        (
            item
            for item in runtimes
            if isinstance(item, dict) and item.get("target") == target
        ),
        None,
    )
    if selected is None or set(selected) != {
        "target",
        "url",
        "sha256",
        "sha512",
        "archive_prefix",
        "interpreter_path",
    }:
        raise ValueError("online contract target is absent or malformed")
    payload = runtime_archive.read_bytes()
    if (
        hashlib.sha256(payload).hexdigest() != selected["sha256"]
        or hashlib.sha512(payload).hexdigest() != selected["sha512"]
    ):
        raise ValueError(
            "online contract runtime archive does not match committed pins"
        )
    output.mkdir(parents=True, exist_ok=False)
    pyz = zipapp()
    npm = valid_npm(pyz)
    document = lock_document(npm, payload, pyz)
    document["runtimes"] = runtimes
    acquisition = document["acquisition"]
    if not isinstance(acquisition, dict):
        raise TypeError("fixture acquisition must be an object")
    acquisition["selected_target"] = target
    (output / "npm.tgz").write_bytes(npm)
    (output / "runtime.lock.json").write_text(
        json.dumps(document, sort_keys=True), encoding="utf-8"
    )
    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--serve", nargs=4, metavar=("ROOT", "PORT_FILE", "CERT", "KEY")
    )
    parser.add_argument(
        "--online-contract",
        nargs=3,
        metavar=("RUNTIME_ARCHIVE", "TARGET", "OUTPUT"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    if arguments.online_contract is not None:
        runtime_path, selected_target, destination = arguments.online_contract
        raise SystemExit(
            write_online_contract(
                Path(runtime_path), selected_target, Path(destination)
            )
        )
    if arguments.serve is None:
        raise SystemExit(main())
    raise SystemExit(serve_fixtures(*(Path(value) for value in arguments.serve)))
