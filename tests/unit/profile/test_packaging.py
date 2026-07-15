from __future__ import annotations

import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

from .test_loader import profile_yaml


def test_no_isolation_build_backend_is_pinned_in_dev_requirements() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    backend_requirement = project["build-system"]["requires"][0]
    dev_requirements = (
        Path("requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    )
    assert backend_requirement in dev_requirements


def test_built_wheel_installs_both_profile_schemas_and_loader_uses_them(
    tmp_path: Path,
) -> None:
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
            ".",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_dir.glob("agentharness-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "agentharness/schemas/profile-v1.json" in names
    assert "agentharness/schemas/local-override-v1.json" in names

    installed = tmp_path / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(installed),
            str(wheel),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(profile_yaml(), encoding="utf-8")
    script = (
        "from pathlib import Path; "
        "from agentharness.profile import load_profile_text; "
        "p=load_profile_text(Path('profile.yaml').read_text()); "
        "assert p.schema_version == 1"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(installed)
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
