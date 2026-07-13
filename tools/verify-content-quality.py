#!/usr/bin/env python3
"""Content-quality gate (P1-08): catches structural doc/content bugs that
markdown-links and markdownlint don't — bad YAML, malformed skill
frontmatter, syntax errors in docs whose Python or bash examples are
explicitly maintained as tested, runnable reference implementations (not
every illustrative snippet in the repo — most are deliberately partial
pseudocode, and syntax-checking those would just be noise);
duplicate-policy detection (B7): the same numeric mandate restated with a
*different* number somewhere outside its source of truth; and
generated-file drift for AGENTS.md (P2-02) and MANIFEST.md (B2) against
their structured sources.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import yaml


class PolicyRegistryEntry(TypedDict):
    name: str
    source_rel: str
    topic_word: re.Pattern[str]

REPO_ROOT = Path(__file__).resolve().parent.parent

# Docs whose fenced ```python blocks are meant to be complete, runnable
# examples — not every doc with a python fence qualifies (see module
# docstring). Add a file here only when its example is verified to run
# end-to-end, the same way these two were.
PYTHON_SNIPPET_SOURCES = [
    REPO_ROOT / "patterns/agentic-loops/README.md",
    REPO_ROOT / "patterns/logging/LOGGING_STANDARDS.md",
]

# B3: same allowlist principle as PYTHON_SNIPPET_SOURCES, extended to the
# docs whose ```bash fences are complete, runnable recipes rather than
# illustrative fragments — docs/INTEGRATION.md's harness-link.sh
# invocations and COVERAGE_REQUIREMENTS.md's bc-based coverage
# comparison. Deliberately NOT languages/*/CONVENTIONS.md,
# patterns/testing/TDD.md, or patterns/error-handling/README.md — those
# are intentional pseudocode/pattern illustrations (variable names like
# `<command>`, partial control flow), and syntax-checking them would be
# exactly the noise this module's docstring already warns against.
BASH_SNIPPET_SOURCES = [
    REPO_ROOT / "docs/INTEGRATION.md",
    REPO_ROOT / "patterns/testing/COVERAGE_REQUIREMENTS.md",
]

# B3: docs/DEMO.md's ```console blocks interleave prompts ("$ cmd"),
# commands' own output, and box-drawing decoration in the same fence —
# not raw bash. Only the "$ "-prefixed lines are commands; extracting
# just those and syntax-checking them is what actually protects this
# doc, since every command in it was hand-verified by running it for
# real when the doc was written (see its own intro paragraph).
CONSOLE_SNIPPET_SOURCES = [
    REPO_ROOT / "docs/DEMO.md",
]

FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)
PYTHON_FENCE_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)
BASH_FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)
CONSOLE_FENCE_RE = re.compile(r"```console\n(.*?)```", re.DOTALL)
ANY_FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)

# B7: duplicate-policy detection. Registry of (name, source-of-truth file,
# topic word) triples for numeric mandates this repo has *actually*
# drifted on before (the coverage floor was independently reconciled from
# a 79%/75%/80% three-way conflict — see CHANGELOG.md's v0.1.0 entry).
#
# Deliberately NOT "flag any percentage near the topic word" — a first
# pass at that flagged .claude/skills/agentic-loops/SKILL.md's "(100%
# coverage)" as a mandate conflict, when it's actually describing that
# one file's *measured* test result, not restating what the mandate
# requires. And a stricter "flag any restatement without a nearby
# cross-reference" design was rejected too:
# patterns/testing/COMPLETION_CHECKLIST.md alone legitimately repeats
# "80%" a dozen times as checklist shorthand, none of it wrong, and
# flagging every occurrence would be almost pure noise (the
# ~15-false-positive risk ROADMAP.md's prior analysis already named).
#
# What's left, cheap to get right, and unambiguous: a number near the
# topic word AND near a *mandate-signal* word/symbol (minimum, required,
# floor, at least, below, >=, <) — "80% coverage minimum" and "coverage
# drops below 80%" both count; "(100% coverage)" describing a measured
# result does not, because nothing near it signals a requirement.
DUPLICATE_POLICY_REGISTRY: list[PolicyRegistryEntry] = [
    {
        "name": "test coverage percentage mandate",
        "source_rel": "patterns/testing/COVERAGE_REQUIREMENTS.md",
        "topic_word": re.compile(r"coverage", re.IGNORECASE),
    },
]

_PERCENT_RE = re.compile(r"\b(\d{1,3})%")
_MANDATE_SIGNAL_RE = re.compile(
    r"minimum|floor|required?|requirement|mandatory|at least|no less than"
    r"|>=|<=?|below|must\s+(?:have|be|reach)",
    re.IGNORECASE,
)

# Historical/generated/fixture content isn't live policy prose — scanning
# it would just surface old snapshots and illustrative examples as if they
# were current, contradictory policy.
DUPLICATE_POLICY_EXCLUDED_DIR_PREFIXES = ("docs/operational/", "examples/")
DUPLICATE_POLICY_EXCLUDED_FILENAMES = {"MANIFEST.md", "AGENTS.md", "CHANGELOG.md"}


def find_yaml_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.yaml", "*.yml"):
        files.extend(REPO_ROOT.rglob(pattern))
    return [f for f in files if ".git" not in f.parts]


def check_yaml_files() -> list[str]:
    errors = []
    for path in find_yaml_files():
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid YAML — {exc}")
    return errors


def check_skill_frontmatter() -> list[str]:
    errors: list[str] = []
    skills_dir = REPO_ROOT / ".claude/skills"
    if not skills_dir.is_dir():
        return errors
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: missing")
            continue
        text = skill_md.read_text()
        match = FRONTMATTER_RE.match(text)
        if not match:
            errors.append(
                f"{skill_md.relative_to(REPO_ROOT)}: no --- frontmatter block found"
            )
            continue
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: invalid frontmatter YAML — {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: frontmatter is not a mapping")
            continue
        name = data.get("name")
        if name != skill_dir.name:
            errors.append(
                f"{skill_md.relative_to(REPO_ROOT)}: frontmatter name "
                f"{name!r} doesn't match directory name {skill_dir.name!r}"
            )
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{skill_md.relative_to(REPO_ROOT)}: missing or empty description")
    return errors


def check_python_snippets() -> list[str]:
    errors = []
    for path in PYTHON_SNIPPET_SOURCES:
        if not path.is_file():
            errors.append(f"{path.relative_to(REPO_ROOT)}: expected file not found")
            continue
        text = path.read_text()
        for i, block in enumerate(PYTHON_FENCE_RE.findall(text), start=1):
            try:
                ast.parse(block)
            except SyntaxError as exc:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: python snippet #{i} has a syntax error — {exc}"
                )
    return errors


def check_manifest_md_sync() -> list[str]:
    # B2: MANIFEST.md is generated from manifest.yaml by
    # tools/generate-manifest.py, not hand-maintained — exact mirror of
    # check_agents_md_sync() above, same drift class, same fix.
    committed = REPO_ROOT / "MANIFEST.md"
    generator = REPO_ROOT / "tools/generate-manifest.py"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        [sys.executable, str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-manifest.py --output MANIFEST.md' and commit the result"
        ]
    return []


def main() -> int:
    errors = []
    errors += check_yaml_files()
    errors += check_skill_frontmatter()
    errors += check_python_snippets()
    errors += check_bash_snippets()
    errors += check_console_snippets()
    errors += check_duplicate_policy_numbers()
    errors += check_agents_md_sync()
    errors += check_manifest_md_sync()

    if errors:
        print("Content-quality check failed:\n")
        for err in errors:
            print(f"  ✗ {err}")
        print(f"\n{len(errors)} issue(s) found.")
        return 1

    print("Content-quality check passed: YAML parses, skill frontmatter valid, "
          "tested Python/bash/console snippets parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
