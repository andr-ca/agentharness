from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"
DEV_REQUIREMENTS = ROOT / "requirements-dev.txt"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
SEED_HELPER = ROOT / "tools/runtime/seed-runtime-artifacts.sh"
LOCAL_CHECK = ROOT / "tools/check.sh"
MANIFEST_SOURCE = ROOT / "manifest.yaml"
CI_RUNTIME_LOCK = ROOT / "requirements-ci-runtime.lock"
CI_CONTENT_LOCK = ROOT / "requirements-ci-content.lock"


def _workflow() -> dict[str, object]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _commands(job: dict[str, object]) -> str:
    steps = job["steps"]
    assert isinstance(steps, list)
    return "\n".join(
        str(step.get("run", "")) for step in steps if isinstance(step, dict)
    )


def test_dev_requirements_contains_only_dev_tools() -> None:
    meaningful = [
        line.strip()
        for line in DEV_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert meaningful
    assert all("requirements-runtime.lock" not in line for line in meaningful)
    assert all(not line.startswith(("-r", "--requirement")) for line in meaningful)


def test_contributor_setup_documents_wheel_only_runtime_then_dev_install() -> None:
    source = CONTRIBUTING.read_text(encoding="utf-8")
    assert "Python 3.12" in source
    assert "Python 3.14" in source
    assert "Python 3.13 is intentionally unsupported" in source
    runtime_install = (
        "python3 -m pip install --require-hashes --only-binary=:all: --no-deps "
        "-r requirements-ci-runtime.lock"
    )
    dev_install = "python3 -m pip install -r requirements-dev.txt"
    assert runtime_install in source
    assert dev_install in source
    assert source.index(runtime_install) < source.index(dev_install)


def test_full_dev_ci_jobs_install_hashed_wheels_before_dev_tools() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    expected = {
        "hook-tests",
        "python-tests",
    }
    actual = {
        name
        for name, raw_job in jobs.items()
        if isinstance(raw_job, dict)
        and "requirements-dev.txt" in _commands(raw_job)
    }
    assert actual == expected
    for name in sorted(expected):
        raw_job = jobs[name]
        assert isinstance(raw_job, dict)
        commands = _commands(raw_job)
        runtime_install = (
            "python3 -m pip install --require-hashes --only-binary=:all: --no-deps "
                "-r requirements-ci-runtime.lock"
        )
        dev_install = "python3 -m pip install -r requirements-dev.txt"
        assert commands.count(runtime_install) == 1, name
        assert commands.count(dev_install) == 1, name
        assert commands.index(runtime_install) < commands.index(dev_install), name


def test_ci_wheel_locks_align_with_canonical_runtime_versions() -> None:
    canonical = (ROOT / "requirements-runtime.lock").read_text(encoding="utf-8")
    runtime = CI_RUNTIME_LOCK.read_text(encoding="utf-8")
    content = CI_CONTENT_LOCK.read_text(encoding="utf-8")
    for requirement in ("PyYAML==6.0.3", "fastjsonschema==2.21.2"):
        assert requirement in canonical
        assert requirement in runtime
    assert "PyYAML==6.0.3" in content
    assert "fastjsonschema" not in content
    assert "--only-binary :all:" in runtime
    assert "--only-binary :all:" in content
    expected_pyyaml_hashes = {
        "7f047e29dcae44602496db43be01ad42fc6f1cc0d8cd6c83d342306c32270196",
        "fc09d0aa354569bc501d4e787133afc08552722d3ab34836a80547331bb5d4a0",
        "9149cad251584d5fb4981be1ecde53a1ca46c891a79788c0df828d2f166bda28",
        "ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc",
        "8d1fab6bb153a416f9aeb4b8763bc0f22a5586065f86f7664fc23339fc1c1fac",
        "34d5fcd24b8445fadc33f9cf348c1047101756fd760b4dacb5c3e99755703310",
        "501a031947e3a9025ed4405a168e6ef5ae3126c59f90ce0cd6f2bfc477be31b7",
        "c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5",
    }

    def pyyaml_hashes(source: str) -> set[str]:
        block = source.split("PyYAML==6.0.3", 1)[1].split(
            "fastjsonschema", 1
        )[0]
        return set(re.findall(r"sha256:([0-9a-f]{64})", block))

    assert pyyaml_hashes(runtime) == expected_pyyaml_hashes
    assert pyyaml_hashes(content) == expected_pyyaml_hashes


def test_jobs_install_only_the_dependencies_they_need() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    sandbox = _commands(jobs["runtime-upgrade-sandbox"])
    content = _commands(jobs["content-quality"])
    assert "requirements-dev.txt" not in sandbox
    assert "requirements-ci-runtime.lock" in sandbox
    assert "pytest==9.1.1" in sandbox
    assert "requirements-dev.txt" not in content
    assert "requirements-ci-content.lock" in content
    assert "pytest" not in content


def test_runtime_artifact_seed_helper_is_registered_in_manifest() -> None:
    manifest = yaml.safe_load(MANIFEST_SOURCE.read_text(encoding="utf-8"))
    paths = {
        asset["path"]
        for section in manifest["sections"]
        for asset in section["assets"]
    }
    assert {
        "requirements-ci-content.lock",
        "requirements-ci-runtime.lock",
        "src/agentharness/runtime_requirements.py",
        "tools/runtime/seed-runtime-artifacts.py",
        "tools/runtime/seed-runtime-artifacts.sh",
    } <= paths


def test_npm_pack_seeds_runtime_artifacts_before_prepack() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    npm_job = jobs["npm-package"]
    sandbox_job = jobs["runtime-upgrade-sandbox"]
    assert isinstance(npm_job, dict)
    assert isinstance(sandbox_job, dict)
    npm_commands = _commands(npm_job)
    seed = "bash tools/runtime/seed-runtime-artifacts.sh"
    assert npm_commands.count(seed) == 1
    assert npm_commands.index(seed) < npm_commands.index("npm pack")
    assert seed in _commands(sandbox_job)
    npm_steps = npm_job["steps"]
    assert isinstance(npm_steps, list)
    setup_python = [
        index
        for index, step in enumerate(npm_steps)
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/setup-python@")
    ]
    seed_step = next(
        index
        for index, step in enumerate(npm_steps)
        if isinstance(step, dict) and seed in str(step.get("run", ""))
    )
    assert len(setup_python) == 1
    assert setup_python[0] < seed_step


def test_hook_tests_seed_runtime_artifacts_after_dependencies_before_bats() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    hook_job = jobs["hook-tests"]
    assert isinstance(hook_job, dict)
    commands = _commands(hook_job)
    dependency_setup = "python3 -m pip install -r requirements-dev.txt"
    seed = "bash tools/runtime/seed-runtime-artifacts.sh"
    hook_tests = "bats .github/hooks/tests/"
    assert commands.count(seed) == 1
    assert commands.index(dependency_setup) < commands.index(seed)
    assert commands.index(seed) < commands.index(hook_tests)


def test_release_pack_seeds_runtime_artifacts_before_prepack() -> None:
    release = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    job = release["jobs"]["publish"]
    commands = _commands(job)
    seed = "bash tools/runtime/seed-runtime-artifacts.sh"
    assert commands.count(seed) == 1
    assert commands.index(seed) < commands.index("npm pack")
    setup_python = [
        step
        for step in job["steps"]
        if isinstance(step, dict)
        and str(step.get("uses", "")).startswith("actions/setup-python@")
    ]
    assert len(setup_python) == 1


def test_ci_executes_dependency_setup_contracts() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    python_job = jobs["python-tests"]
    assert isinstance(python_job, dict)
    commands = _commands(python_job)
    local = LOCAL_CHECK.read_text(encoding="utf-8")
    for test_path in (
        "tests/unit/runtime/test_ci_dependency_contract.py",
        "tests/unit/runtime/test_seed_runtime_artifacts.py",
    ):
        assert test_path in commands
        assert test_path in local
