#!/usr/bin/env python3
"""Content-quality gate (P1-08): catches structural doc/content bugs that
markdown-links and markdownlint don't — bad YAML, malformed skill
frontmatter, syntax errors in docs whose Python or bash examples are
explicitly maintained as tested, runnable reference implementations (not
every illustrative snippet in the repo — most are deliberately partial
pseudocode, and syntax-checking those would just be noise);
duplicate-policy detection (B7): the same numeric mandate restated with a
*different* number somewhere outside its source of truth; and
generated-file drift for AGENTS.md (P2-02), MANIFEST.md (B2), the
cross-platform-parity adapters (GEMINI.md, .kilo/rules/agentharness.md,
.github/copilot-instructions.md + .github/instructions/*, and
.cursor/rules/*.mdc), and the custom-agent-porting generators
(.codex/agents/*.toml, .opencode/agents/*.md, .cursor/agents/*.md,
.kilo/agents/*.md, .github/agents/*.agent.md, and .gemini/agents/*.md)
against their structured sources.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
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


# Generated/dependency/venv trees a developer might have on disk locally
# (gitignored, so not tracked content) but that rglob() would still walk
# into — scanning them is pure noise at best and a slow/broken run at
# worst (e.g. node_modules can contain thousands of unrelated YAML files).
_YAML_SCAN_EXCLUDED_DIR_NAMES = {".git", "node_modules", "venv", ".venv", "__pycache__"}


def find_yaml_files() -> list[Path]:
    # os.walk() with in-place dirnames pruning, not Path.rglob() filtered
    # afterward — rglob() has no way to skip descending into an excluded
    # directory once it's found one, so a post-hoc filter still pays the
    # full traversal cost of walking into node_modules/venv/etc, which is
    # exactly the slow/noisy case this exists to avoid.
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _YAML_SCAN_EXCLUDED_DIR_NAMES]
        for name in filenames:
            if name.endswith((".yaml", ".yml")):
                files.append(Path(dirpath) / name)
    return files


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


def _display_path(path: Path) -> str:
    # check_bash_snippets()/check_console_snippets() accept an overridable
    # `sources` list (so tests can point them at tmp_path fixtures instead
    # of the real repo) — relative_to(REPO_ROOT) raises ValueError for a
    # path outside it, unlike the other checkers here that only ever see
    # real repo paths.
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _bash_syntax_error(script: str) -> str | None:
    # -n is syntax-check-only — never executes the script (the recipes
    # here do real things like `git submodule add` or `touch`, which must
    # never run as a side effect of linting docs). BASH_ENV is explicitly
    # cleared: a non-interactive bash normally sources it on startup
    # (verified this build's `bash -n` doesn't actually execute it, but
    # that's an implementation detail of one bash version, not a
    # documented guarantee) — this checker shouldn't depend on whatever
    # happens to be in the invoking environment's BASH_ENV.
    env = {**os.environ, "BASH_ENV": ""}
    result = subprocess.run(
        ["bash", "-n"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        return result.stderr.strip()
    return None


def check_bash_snippets(sources: list[Path] = BASH_SNIPPET_SOURCES) -> list[str]:
    errors = []
    for path in sources:
        if not path.is_file():
            errors.append(f"{_display_path(path)}: expected file not found")
            continue
        text = path.read_text()
        for i, block in enumerate(BASH_FENCE_RE.findall(text), start=1):
            error = _bash_syntax_error(block)
            if error:
                errors.append(
                    f"{_display_path(path)}: bash snippet #{i} has a syntax error — {error}"
                )
    return errors


def check_console_snippets(sources: list[Path] = CONSOLE_SNIPPET_SOURCES) -> list[str]:
    errors = []
    for path in sources:
        if not path.is_file():
            errors.append(f"{_display_path(path)}: expected file not found")
            continue
        text = path.read_text()
        for i, block in enumerate(CONSOLE_FENCE_RE.findall(text), start=1):
            commands = "\n".join(
                line[len("$ "):] for line in block.split("\n") if line.startswith("$ ")
            )
            if not commands:
                continue
            error = _bash_syntax_error(commands)
            if error:
                errors.append(
                    f"{_display_path(path)}: console snippet #{i} has a syntax error — {error}"
                )
    return errors


def _strip_fences(text: str) -> str:
    # Fenced code blocks (```...``` / ~~~...~~~) can legitimately contain
    # illustrative "wrong" numbers — e.g. README.md's before/after example
    # of two projects' drifted CLAUDE.md snippets — that aren't this
    # repo's actual live policy and shouldn't be scanned as if they were.
    return ANY_FENCE_RE.sub("", text)


def _extract_mandate_numbers(text: str, topic_word: re.Pattern[str]) -> set[str]:
    # A percentage counts as a mandate statement only if BOTH the topic
    # word (e.g. "coverage") and a mandate-signal word/symbol (minimum,
    # required, below, >=, ...) appear on the SAME line as it — see the
    # registry comment above for why a bare "N% <topic>" isn't enough on
    # its own. Scoped to a single line rather than a character window
    # around the match: a character window bled across adjacent list
    # items in testing, e.g. COMPLETION_CHECKLIST.md's "- [ ] Coverage >=
    # 80% (minimum requirement)" immediately followed by "- [ ] Strive for
    # 90%+ coverage" — a window wide enough to reach "minimum requirement"
    # from the 90% line would have wrongly flagged the aspirational
    # "strive for" stretch goal as a conflicting mandate. Scoping to
    # single lines trades a few missed same-file legitimate mentions that
    # happen to wrap across lines (never counted, never flagged either —
    # safe failure mode) for zero false conflicts from a neighboring line.
    numbers = set()
    for line in text.split("\n"):
        if not (topic_word.search(line) and _MANDATE_SIGNAL_RE.search(line)):
            continue
        for match in _PERCENT_RE.finditer(line):
            numbers.add(match.group(1))
    return numbers


# "worktrees" (no dot) covers Claude Code's agent worktrees at
# .claude/worktrees/ — stale checkouts there are historical snapshots, not
# current repo content, same as .worktrees/.
_MD_SCAN_EXCLUDED_DIR_NAMES = {".git", ".worktrees", "worktrees", "node_modules"}


def _find_markdown_files(scan_root: Path) -> list[Path]:
    # Same os.walk() in-place pruning rationale as find_yaml_files():
    # rglob() can't stop descending into an excluded directory, so a
    # post-hoc parts filter still pays the full traversal cost of walking
    # stale worktree checkouts and node_modules trees.
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(scan_root):
        dirnames[:] = [d for d in dirnames if d not in _MD_SCAN_EXCLUDED_DIR_NAMES]
        for name in filenames:
            if name.endswith(".md"):
                files.append(Path(dirpath) / name)
    return sorted(files)


def check_duplicate_policy_numbers(scan_root: Path = REPO_ROOT) -> list[str]:
    errors = []
    for entry in DUPLICATE_POLICY_REGISTRY:
        source_path = scan_root / entry["source_rel"]
        if not source_path.is_file():
            errors.append(f"{entry['source_rel']}: expected source-of-truth file not found")
            continue
        source_numbers = _extract_mandate_numbers(_strip_fences(source_path.read_text()), entry["topic_word"])

        for md_file in _find_markdown_files(scan_root):
            if md_file == source_path:
                continue
            rel = md_file.relative_to(scan_root)
            rel_str = str(rel)
            if rel_str.startswith(DUPLICATE_POLICY_EXCLUDED_DIR_PREFIXES):
                continue
            if md_file.name in DUPLICATE_POLICY_EXCLUDED_FILENAMES:
                continue

            found_numbers = _extract_mandate_numbers(_strip_fences(md_file.read_text()), entry["topic_word"])
            conflicting = found_numbers - source_numbers
            if conflicting:
                errors.append(
                    f"{rel_str}: states {entry['name']} as {sorted(conflicting)}, "
                    f"but {entry['source_rel']} (source of truth) says "
                    f"{sorted(source_numbers)} — fix the restatement or update the source"
                )
    return errors


def check_agents_md_sync() -> list[str]:
    # P2-02: AGENTS.md is generated from CLAUDE.md + .claude/skills/ by
    # tools/generate-agents-md.sh, not hand-maintained — the same drift
    # class fixed for docs in P1-13, guarded against here the same way
    # verify-manifest.sh guards MANIFEST.md's bidirectional accuracy.
    committed = REPO_ROOT / "AGENTS.md"
    generator = REPO_ROOT / "tools/generate-agents-md.sh"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        ["bash", str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-agents-md.sh --output AGENTS.md' and commit the result"
        ]
    return []


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


_CONTEXT_KIND_VALUES = {"policy", "pattern", "generated", "repository-fact"}
_CONTEXT_LIFECYCLE_VALUES = {"task", "project", "durable"}
_CONTEXT_LOADING_VALUES = {"always-on", "on-demand"}
_CONTEXT_PROVENANCE_VALUES = {"verified", "inferred", "declared", "unknown"}
_CONTEXT_REQUIRED_FIELDS = (
    "id",
    "path",
    "kind",
    "authority",
    "lifecycle",
    "loading",
    "provenance",
    "freshness",
)


def check_context_yaml_valid(scan_root: Path = REPO_ROOT) -> list[str]:
    """Validate context.yaml's schema (Context Plane Slice 1).

    context.yaml is hand-maintained source, like manifest.yaml — not
    generated, so there is no drift check here, only structural
    validation: every entry has the required fields, enum fields hold a
    recognized value, `authority` (when not "none") names a real ladder
    in precedence.yaml, and `path` points at a file that actually exists
    — the same "a malformed or path-missing entry fails CI" contract
    check_manifest_md_sync() already enforces for manifest.yaml, applied
    to the registry instead of the drift-check it doesn't need.
    """
    model_path = scan_root / "context.yaml"
    if not model_path.is_file():
        return []  # consumer repos have no registry; do not fail them

    try:
        raw = model_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"context.yaml: could not be read — {exc}"]

    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return []  # check_yaml_files() already reports malformed YAML

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        return ["context.yaml: no entries declared — schema changed?"]

    precedence_path = scan_root / "precedence.yaml"
    ladder_ids: set[str] = set()
    if precedence_path.is_file():
        try:
            precedence_data = yaml.safe_load(precedence_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            precedence_data = {}
        for ladder in precedence_data.get("ladders") or []:
            if isinstance(ladder, dict) and ladder.get("id"):
                ladder_ids.add(str(ladder["id"]))

    errors: list[str] = []
    seen_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(f"context.yaml: entry {entry!r} is not a mapping")
            continue
        entry_id = str(entry.get("id", "<missing id>"))
        missing = [f for f in _CONTEXT_REQUIRED_FIELDS if f not in entry]
        if missing:
            errors.append(f"context.yaml: entry '{entry_id}' missing field(s): {', '.join(missing)}")
            continue

        if entry_id in seen_ids:
            errors.append(f"context.yaml: duplicate id '{entry_id}'")
        seen_ids.add(entry_id)

        entry_path = scan_root / str(entry["path"])
        if not entry_path.is_file():
            errors.append(f"context.yaml: entry '{entry_id}' points at {entry['path']}, which does not exist")

        if entry["kind"] not in _CONTEXT_KIND_VALUES:
            errors.append(f"context.yaml: entry '{entry_id}' has invalid kind '{entry['kind']}'")
        if entry["lifecycle"] not in _CONTEXT_LIFECYCLE_VALUES:
            errors.append(f"context.yaml: entry '{entry_id}' has invalid lifecycle '{entry['lifecycle']}'")
        if entry["loading"] not in _CONTEXT_LOADING_VALUES:
            errors.append(f"context.yaml: entry '{entry_id}' has invalid loading '{entry['loading']}'")
        if entry["provenance"] not in _CONTEXT_PROVENANCE_VALUES:
            errors.append(f"context.yaml: entry '{entry_id}' has invalid provenance '{entry['provenance']}'")

        authority = entry["authority"]
        if authority != "none" and ladder_ids and authority not in ladder_ids:
            errors.append(
                f"context.yaml: entry '{entry_id}' has authority '{authority}', "
                f"which is not a ladder id in precedence.yaml (or 'none')"
            )

        freshness = entry["freshness"]
        invalidate_on = freshness.get("invalidate_on") if isinstance(freshness, dict) else None
        if (
            not isinstance(freshness, dict)
            or not freshness.get("last_verified")
            or not isinstance(invalidate_on, list)
            or not invalidate_on
        ):
            errors.append(
                f"context.yaml: entry '{entry_id}' has an incomplete freshness "
                "block — needs last_verified and a non-empty invalidate_on list"
            )
            continue

        for watched_path in invalidate_on:
            resolved = _resolve_repo_relative(scan_root, watched_path)
            if resolved is None:
                errors.append(
                    f"context.yaml: entry '{entry_id}' has an invalid invalidate_on "
                    f"entry {watched_path!r} — must be a non-empty repo-relative "
                    "string that stays inside the repo"
                )
            elif not resolved.exists():
                errors.append(
                    f"context.yaml: entry '{entry_id}' watches {watched_path} "
                    "in invalidate_on, which does not exist"
                )

    return errors


def _resolve_repo_relative(scan_root: Path, candidate: object) -> Path | None:
    """A repo-relative path, resolved and checked to stay inside scan_root.

    Rejects non-strings, empty strings, absolute paths, and traversal
    (`../`) that would otherwise let a malformed context.yaml entry
    point check_context_yaml_valid()/check_context_freshness() at
    something outside the repo (e.g. `/etc/passwd`).
    """
    if not isinstance(candidate, str) or not candidate.strip():
        return None
    resolved = (scan_root / candidate).resolve()
    try:
        resolved.relative_to(scan_root.resolve())
    except ValueError:
        return None
    return resolved


def _is_shallow_git_checkout(scan_root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=scan_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == "true"


def _git_last_change_date(scan_root: Path, rel_path: str) -> str | None:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", rel_path],
        cwd=scan_root,
        capture_output=True,
        text=True,
        check=False,
    )
    date = result.stdout.strip()
    return date or None


def check_context_freshness(scan_root: Path = REPO_ROOT) -> tuple[list[str], list[str]]:
    """Slice 3: flag context.yaml entries whose watched paths changed
    more recently than the entry's own last_verified date.

    Generalizes check_manifest_md_sync()'s one-hardcoded-pair pattern to
    every registered entry (#193 item 3, #198). Returns (errors,
    warnings) rather than a single list: staleness is a warning for most
    entries (advisory content can lag its review), but a hard failure for
    entries whose `authority` names a real precedence.yaml ladder — those
    are rule-defining artifacts, and "rules may not" lag per #198.

    Entries with malformed freshness data are check_context_yaml_valid()'s
    job to report, not this function's — it silently skips what it can't
    evaluate rather than double-reporting the same defect.
    """
    model_path = scan_root / "context.yaml"
    if not model_path.is_file():
        return [], []

    try:
        data = yaml.safe_load(model_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return [], []

    if _is_shallow_git_checkout(scan_root):
        # A shallow clone's `git log -- <path>` can only see the tip
        # commit, so every watched path looks like it "changed" at the
        # checkout's HEAD date regardless of its real history — a false
        # positive on every entry, not a partial signal. Skip rather than
        # report staleness neither confirmed nor ruled out. The gate's own
        # CI job fetches full history (fetch-depth: 0); this guards any
        # other caller (a different CI job, a contributor's shallow
        # clone) that doesn't.
        return [], []

    errors: list[str] = []
    warnings: list[str] = []
    # Many entries share a watched path (every generated-adapter entry
    # watches CLAUDE.md, for instance) — cache each path's git lookup
    # once per run instead of re-shelling out to `git log` for every
    # entry that watches it.
    change_date_cache: dict[str, str | None] = {}

    for entry in data.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        entry_id = str(entry.get("id", "<missing id>"))
        freshness = entry.get("freshness")
        if not isinstance(freshness, dict):
            continue
        last_verified = freshness.get("last_verified")
        invalidate_on = freshness.get("invalidate_on")
        if not last_verified or not isinstance(invalidate_on, list) or not invalidate_on:
            continue

        stale_on: list[str] = []
        for watched_path in invalidate_on:
            if _resolve_repo_relative(scan_root, watched_path) is None:
                continue  # check_context_yaml_valid()'s job to report, not this one's
            watched_str = str(watched_path)
            if watched_str not in change_date_cache:
                change_date_cache[watched_str] = _git_last_change_date(scan_root, watched_str)
            changed = change_date_cache[watched_str]
            if changed and changed[:10] > str(last_verified)[:10]:
                stale_on.append(watched_str)

        if not stale_on:
            continue

        message = (
            f"context.yaml: entry '{entry_id}' is stale — {', '.join(stale_on)} "
            f"changed after last_verified ({last_verified}); bump last_verified "
            "in the same commit that re-reviews it"
        )
        if entry.get("authority") not in (None, "none"):
            errors.append(message)
        else:
            warnings.append(message)

    return errors, warnings


def check_gemini_md_sync() -> list[str]:
    # Cross-platform parity: GEMINI.md is generated from CLAUDE.md +
    # .claude/skills/ by tools/generate-gemini-md.sh, exact mirror of
    # check_agents_md_sync() above — same drift class, same fix.
    committed = REPO_ROOT / "GEMINI.md"
    generator = REPO_ROOT / "tools/generate-gemini-md.sh"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        ["bash", str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-gemini-md.sh --output GEMINI.md' and commit the result"
        ]
    return []


def check_qwen_md_sync() -> list[str]:
    # Cross-platform parity: QWEN.md is generated from CLAUDE.md +
    # .claude/skills/ by tools/generate-qwen-md.sh, exact mirror of
    # check_gemini_md_sync() above — same drift class, same fix.
    committed = REPO_ROOT / "QWEN.md"
    generator = REPO_ROOT / "tools/generate-qwen-md.sh"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        ["bash", str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-qwen-md.sh --output QWEN.md' and commit the result"
        ]
    return []


def check_kilo_rules_sync() -> list[str]:
    # Cross-platform parity: .kilo/rules/agentharness.md is generated by
    # tools/generate-kilo-rules.sh, exact mirror of check_agents_md_sync().
    committed = REPO_ROOT / ".kilo/rules/agentharness.md"
    generator = REPO_ROOT / "tools/generate-kilo-rules.sh"
    if not committed.is_file():
        return [f"{committed.relative_to(REPO_ROOT)}: expected file not found"]
    result = subprocess.run(
        ["bash", str(generator)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
    if result.stdout != committed.read_text():
        return [
            f"{committed.relative_to(REPO_ROOT)}: out of sync with its source — "
            f"run 'tools/generate-kilo-rules.sh --output .kilo/rules/agentharness.md' and commit the result"
        ]
    return []


def _diff_generated_subdir(
    tmp_root: Path, subdir_rel: str, regen_hint: str, ignore: set[str] | None = None
) -> list[str]:
    # Shared by check_copilot_instructions_sync and check_cursor_rules_sync:
    # both own an entire directory of generated files (a variable set —
    # one per language or per skill — not a single fixed path), so drift
    # means comparing the whole subdirectory in both directions: a file
    # the generator produces that isn't committed (drift), and a
    # committed file the generator no longer produces (a stale leftover
    # from a removed language/skill).
    #
    # `ignore` exists for the one case where the output directory isn't
    # exclusively generator output: .opencode/agents/ is also opencode's
    # own fixed (non-configurable) custom-agent location, so
    # issue-analyzer.md lives there hand-authored, not ported from
    # .claude/agents/ — see check_opencode_agents_sync().
    generated_root = tmp_root / subdir_rel
    committed_root = REPO_ROOT / subdir_rel
    ignore_paths = {Path(p) for p in (ignore or set())}
    generated_files = (
        {p.relative_to(generated_root) for p in generated_root.rglob("*") if p.is_file()}
        if generated_root.is_dir() else set()
    )
    committed_files = (
        {
            p.relative_to(committed_root)
            for p in committed_root.rglob("*")
            if p.is_file()
        } - ignore_paths
        if committed_root.is_dir() else set()
    )
    errors = []
    for rel in sorted(generated_files - committed_files):
        errors.append(f"{subdir_rel}/{rel}: generated but missing from the committed tree — {regen_hint}")
    for rel in sorted(committed_files - generated_files):
        errors.append(f"{subdir_rel}/{rel}: committed but no longer generated — {regen_hint}")
    for rel in sorted(generated_files & committed_files):
        if (generated_root / rel).read_text() != (committed_root / rel).read_text():
            errors.append(f"{subdir_rel}/{rel}: out of sync with its source — {regen_hint}")
    return errors


def check_copilot_instructions_sync() -> list[str]:
    # Cross-platform parity: .github/copilot-instructions.md +
    # .github/instructions/*.instructions.md are generated by
    # tools/generate-copilot-instructions.sh, not hand-maintained.
    generator = REPO_ROOT / "tools/generate-copilot-instructions.sh"
    regen_hint = "run 'tools/generate-copilot-instructions.sh --output-dir .' and commit the result"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["bash", str(generator), str(REPO_ROOT), "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]

        errors = []
        committed_main = REPO_ROOT / ".github/copilot-instructions.md"
        generated_main = tmp_path / ".github/copilot-instructions.md"
        if not committed_main.is_file():
            errors.append(f"{committed_main.relative_to(REPO_ROOT)}: expected file not found")
        elif generated_main.read_text() != committed_main.read_text():
            errors.append(f"{committed_main.relative_to(REPO_ROOT)}: out of sync with its source — {regen_hint}")

        errors += _diff_generated_subdir(tmp_path, ".github/instructions", regen_hint)
        return errors


def check_cursor_rules_sync() -> list[str]:
    # Cross-platform parity: .cursor/rules/*.mdc are generated by
    # tools/generate-cursor-rules.sh — the whole directory is exclusively
    # generator output, so a plain subdirectory diff suffices.
    generator = REPO_ROOT / "tools/generate-cursor-rules.sh"
    regen_hint = "run 'tools/generate-cursor-rules.sh --output-dir .' and commit the result"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["bash", str(generator), str(REPO_ROOT), "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"{generator.relative_to(REPO_ROOT)}: failed to run — {result.stderr.strip()}"]
        return _diff_generated_subdir(tmp_path, ".cursor/rules", regen_hint)


def _check_agent_generator_sync(
    generator_rel: str, output_subdir_rel: str, ignore: set[str] | None = None
) -> list[str]:
    # Shared by the six custom-agent-porting generators
    # (Codex/OpenCode/Cursor/Kilo/Copilot/Gemini) below — each owns a whole directory
    # of variable-length output (one file per .claude/agents/*.md), the
    # same shape check_cursor_rules_sync() already handles via
    # _diff_generated_subdir().
    generator = REPO_ROOT / generator_rel
    regen_hint = f"run '{generator_rel} --output-dir .' and commit the result"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["bash", str(generator), str(REPO_ROOT), "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return [f"{generator_rel}: failed to run — {result.stderr.strip()}"]
        return _diff_generated_subdir(tmp_path, output_subdir_rel, regen_hint, ignore)


def check_codex_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-codex-agents.sh", ".codex/agents"
    )


def check_opencode_agents_sync() -> list[str]:
    # .opencode/agents/ is opencode's own fixed, non-configurable
    # custom-agent location — issue-analyzer.md lives there hand-authored
    # for .github/workflows/issue-analysis.yml (issue #107), not ported
    # from .claude/agents/, so it's excluded from the generator diff.
    return _check_agent_generator_sync(
        "tools/generate-opencode-agents.sh",
        ".opencode/agents",
        ignore={"issue-analyzer.md"},
    )


def check_cursor_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-cursor-agents.sh", ".cursor/agents"
    )


def check_kilo_agents_sync() -> list[str]:
    return _check_agent_generator_sync("tools/generate-kilo-agents.sh", ".kilo/agents")


def check_copilot_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-copilot-agents.sh", ".github/agents"
    )


def check_gemini_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-gemini-agents.sh", ".gemini/agents"
    )


def check_qwen_agents_sync() -> list[str]:
    return _check_agent_generator_sync(
        "tools/generate-qwen-agents.sh", ".qwen/agents"
    )


# Absence claims in KNOWN_LIMITATIONS.md, e.g.
#   - **Patterns:** no API-design pattern yet.
# Captures the asset name and the asset kind so a claim about a *pattern*
# isn't silenced by a *skill* that happens to share the name.
_ABSENCE_CLAIM = re.compile(
    r"\bno\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s+(pattern|skill)\b",
    re.IGNORECASE,
)

# Which manifest path prefix answers a claim about each asset kind.
_KIND_ROOTS = {
    "pattern": ("patterns/",),
    "skill": (".claude/skills/", ".agents/skills/"),
}


_FORCE_PUSH_RE = re.compile(r"git\s+push\b[^\n]*--force(-with-lease)?\b")

# Declared inside a fence to mark a deliberate, documented exception —
# history rewriting to purge a leaked secret is the real one. Declaring it
# beats allowlisting a path: the justification lives next to the command,
# and a new exception cannot appear without saying so.
FORCE_PUSH_EXCEPTION_MARKER = "agentharness:force-push-exception"


def check_no_force_push_instructions(scan_root: Path = REPO_ROOT) -> list[str]:
    """Flag docs that *instruct* a reader to force-push.

    The repo-wide `no-force-push-any-branch` ruleset has no bypass actors,
    so a non-fast-forward push is rejected on every branch —
    `--force-with-lease` included, since its lease check protects against
    clobbering someone else's work but does not make the push
    fast-forward. Any doc telling a reader to do it is advice that cannot
    work, and they discover that only when the push fails.

    Deliberately narrow, in the same spirit as DUPLICATE_POLICY_REGISTRY:
    one targeted rule with real instances, not a general same-rule-drift
    detector. A general one would need per-rule exclusions for the rule's
    own statement, tests, and changelog history — rivalling the rule count.

    Only commands inside fenced blocks count, and commented lines do not.
    Prose explaining *why* force-pushing is blocked must not trip the
    check, or fixing a violation would itself be a violation.

    Genuine exceptions exist — purging a leaked secret from history
    requires rewriting it — and are declared with the marker below inside
    the fence. Declaring rather than path-allowlisting keeps every
    exception visible and self-justifying in the doc that needs it, and
    means a new one cannot appear silently.
    """
    errors: list[str] = []
    for path in _find_markdown_files(scan_root):
        rel = path.relative_to(scan_root).as_posix()
        if rel.startswith(("docs/operational/", "CHANGELOG")):
            continue  # historical records, not live instruction
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for fence in ANY_FENCE_RE.findall(text):
            if FORCE_PUSH_EXCEPTION_MARKER in fence:
                continue
            for line in fence.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue  # a comment is explanation, not instruction
                if _FORCE_PUSH_RE.search(stripped):
                    errors.append(
                        f"{rel}: instructs a force-push (`{stripped}`), which the "
                        "no-force-push-any-branch ruleset rejects on every branch "
                        "— recommend fetch + rebase instead"
                    )
    return errors


def check_precedence_matches_docs(scan_root: Path = REPO_ROOT) -> list[str]:
    """Assert the prose precedence ladders still match precedence.yaml.

    The repo has two independent "which rule wins" orderings, and both
    lived only in prose across three separate places with nothing checking
    they agreed. precedence.yaml is the declared source; this keeps the
    documentation honest against it, the same way MANIFEST.md is checked
    against manifest.yaml.

    Order is the whole content of a precedence rule, so a doc listing the
    right levels in the wrong sequence is a failure, not untidiness.
    """
    model_path = scan_root / "precedence.yaml"
    # is_file(), not exists(): a directory or symlink-to-nothing named
    # precedence.yaml passes exists() and then makes read_text() raise,
    # crashing the whole content-quality gate instead of reporting.
    if not model_path.is_file():
        if model_path.exists():
            return [
                "precedence.yaml: exists but is not a regular file — "
                "expected a YAML file"
            ]
        return []  # consumer repos have no model; do not fail them

    try:
        raw = model_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"precedence.yaml: could not be read — {exc}"]

    try:
        model = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return []  # check_yaml_files() already reports malformed YAML

    ladders = model.get("ladders") or []
    if not ladders:
        # A model that parses to nothing would make every prose doc pass.
        return ["precedence.yaml: no ladders declared — schema changed?"]

    errors: list[str] = []
    for ladder in ladders:
        if not isinstance(ladder, dict):
            continue
        ladder_id = ladder.get("id", "<unnamed>")
        doc_rel = str(ladder.get("documented_in", ""))
        doc_path = scan_root / doc_rel
        if not doc_path.is_file():
            errors.append(
                f"precedence.yaml: ladder '{ladder_id}' points at "
                f"{doc_rel}, which does not exist"
            )
            continue

        try:
            prose = doc_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{doc_rel}: could not be read — {exc}")
            continue
        levels = sorted(
            (lv for lv in (ladder.get("levels") or []) if isinstance(lv, dict)),
            key=lambda lv: lv.get("rank", 0),
        )

        # Where each level's summary first appears in the prose. A level
        # the doc never mentions is missing; levels appearing out of
        # sequence mean the doc contradicts the declared order.
        positions: list[int] = []
        for level in levels:
            # doc_match when present: the distinctive phrase to find in
            # the prose, kept separate from the summary so the model can
            # describe a level in its own words without being coupled to
            # any one document's phrasing.
            summary = str(
                level.get("doc_match") or level.get("summary", "")
            ).strip()
            if not summary:
                continue
            index = prose.find(summary)
            if index < 0:
                errors.append(
                    f"{doc_rel}: precedence level '{summary}' "
                    f"(rank {level.get('rank')}, ladder '{ladder_id}') "
                    "is not documented — update the prose or precedence.yaml"
                )
            else:
                positions.append(index)

        if len(positions) > 1 and positions != sorted(positions):
            errors.append(
                f"{doc_rel}: precedence levels for ladder '{ladder_id}' "
                "appear in a different order than precedence.yaml declares "
                "— order is the substance of a precedence rule, so one of "
                "the two is wrong"
            )

    return errors


def _manifest_asset_paths(data: object) -> list[str]:
    """Every asset `path` in manifest.yaml, which nests them under
    sections[].assets[] rather than a flat top-level list."""
    if not isinstance(data, dict):
        return []
    paths: list[str] = []
    for section in data.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for asset in section.get("assets") or []:
            if isinstance(asset, dict) and asset.get("path"):
                paths.append(str(asset["path"]))
    return paths


def check_absence_claims_match_manifest(scan_root: Path = REPO_ROOT) -> list[str]:
    """Flag "no X yet" claims that manifest.yaml contradicts.

    KNOWN_LIMITATIONS.md is hand-maintained and states what the harness does
    not have yet. Those claims go stale silently the moment the thing gets
    built, and nothing notices: the file said "no API-design pattern yet"
    while patterns/api-design/, a skill, and manifest.yaml all had it.

    manifest.yaml can answer this class of claim mechanically, so derive the
    answer instead of relying on someone remembering to update prose. Scoped
    deliberately to absence claims about patterns and skills — the kinds the
    manifest actually inventories — rather than every sentence in the file.
    """
    limitations = scan_root / "docs" / "KNOWN_LIMITATIONS.md"
    manifest = scan_root / "manifest.yaml"
    # is_file() for the same reason as above — exists() is true for a
    # directory, and read_text() would then crash the gate.
    if not limitations.is_file() or not manifest.is_file():
        return []

    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []  # check_yaml_files() already reports malformed YAML

    paths = _manifest_asset_paths(data)
    if not paths:
        # Extracting nothing would make every absence claim silently pass.
        # That is a schema change, not a clean bill of health — say so
        # rather than reporting success for the wrong reason.
        return ["manifest.yaml: no asset paths found — schema changed?"]

    errors = []
    parsed_claims = 0
    try:
        limitations_text = limitations.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"docs/KNOWN_LIMITATIONS.md: could not be read — {exc}"]

    for line_no, line in enumerate(limitations_text.splitlines(), 1):
        for match in _ABSENCE_CLAIM.finditer(line):
            parsed_claims += 1
            name, kind = match.group(1).lower(), match.group(2).lower()
            roots = _KIND_ROOTS.get(kind, ())
            hit = next(
                (
                    path
                    for path in paths
                    if any(path.lower().startswith(f"{root}{name}/") for root in roots)
                ),
                None,
            )
            if hit:
                errors.append(
                    f"docs/KNOWN_LIMITATIONS.md:{line_no}: claims no '{name}' {kind}, "
                    f"but manifest.yaml lists {hit} — correct the claim or remove it"
                )

    # A file with zero parseable claims is almost certainly a rewording
    # that slipped out of the recognized form, not a file that genuinely
    # asserts no absences. Reported so the check cannot be silently
    # disabled by prose — which is exactly how the first version of this
    # very fix regressed: "no GraphQL, messaging/event-driven, or caching
    # pattern yet" reads fine and matches nothing.
    if parsed_claims == 0:
        errors.append(
            "docs/KNOWN_LIMITATIONS.md: no absence claims matched the "
            "'no <name> pattern|skill' form — reword them into that shape "
            "so they stay machine-checked, or remove this check"
        )
    return errors


def main() -> int:
    errors = []
    errors += check_yaml_files()
    errors += check_skill_frontmatter()
    errors += check_python_snippets()
    errors += check_bash_snippets()
    errors += check_console_snippets()
    errors += check_duplicate_policy_numbers()
    errors += check_absence_claims_match_manifest()
    errors += check_precedence_matches_docs()
    errors += check_no_force_push_instructions()
    errors += check_agents_md_sync()
    errors += check_manifest_md_sync()
    errors += check_context_yaml_valid()
    freshness_errors, freshness_warnings = check_context_freshness()
    errors += freshness_errors
    errors += check_gemini_md_sync()
    errors += check_qwen_md_sync()
    errors += check_kilo_rules_sync()
    errors += check_copilot_instructions_sync()
    errors += check_cursor_rules_sync()
    errors += check_codex_agents_sync()
    errors += check_opencode_agents_sync()
    errors += check_cursor_agents_sync()
    errors += check_kilo_agents_sync()
    errors += check_copilot_agents_sync()
    errors += check_gemini_agents_sync()
    errors += check_qwen_agents_sync()

    if freshness_warnings:
        print("Content-quality warnings (non-fatal — advisory context.yaml entries):\n")
        for warn in freshness_warnings:
            print(f"  ! {warn}")
        print()

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
