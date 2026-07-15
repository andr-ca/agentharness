---
name: file-placement-policy
description: "Use before creating any new file or directory in an established project — covers guarded root paths, docs/, src/, conf/, the allowed-additions escape hatch, and how to ask for permission. Load this skill at the start of every session in a project that has .agentharness-guarded-paths.json."
metadata:
  type: skills
  complexity: low
  scope: [all]
---

# File Placement Policy

**Load this skill at session start** if the project has
`.agentharness-guarded-paths.json`. Read the file before touching anything.

---

## Rule: check before creating

Before creating any new file or directory, check whether the target
location is guarded:

```bash
python3 -c "
import json
d = json.load(open('.agentharness-guarded-paths.json'))
print('Root guarded:', d['guard_root_level_new_items'])
print('Guarded dirs:', d['guarded_dirs'])
"
```

If the path is guarded: **stop and ask the user for permission.**

---

## What counts as guarded

- Any new file at the root level (when `guard_root_level_new_items: true`)
- Any file under `src/`, `docs/`, `tests/`, `conf/`, `logs/`, etc.
- Any root-level config file already listed in `guarded_root_files`

---

## Asking for permission

> "I need to create `docs/architecture/NEW_SECTION.md` to document X.
> This is in the guarded `docs/` directory. May I proceed?"

Wait for an explicit `yes`/`ok`/`go ahead` response.

---

## After getting permission: record it

Add the approved path to `.agentharness-allowed-additions.txt`:

```bash
echo "docs/architecture/NEW_SECTION.md" >> .agentharness-allowed-additions.txt
```

The pre-commit hook reads this file to allow the commit.

---

## No guarded-paths file = early-stage project

If `.agentharness-guarded-paths.json` doesn't exist:

1. Run: `python3 tools/analyze_structure.py . --recommend`
2. Present the recommendations to the user.
3. If accepted, create the structure and generate the config:
   `python3 tools/analyze_structure.py . --output .agentharness-guarded-paths.json`

---

## Pre-commit enforcement

The hook at `tools/check-file-placement.sh` runs automatically before
every commit. If a staged file is in a guarded location and not in
`.agentharness-allowed-additions.txt`, the commit is blocked with a
clear message.

---

## Reference

Full protocol: `patterns/file-placement-policy/POLICY.md`
Analyzer: `tools/analyze_structure.py`
Hook: `tools/check-file-placement.sh`
