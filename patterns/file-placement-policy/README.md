# File Placement Policy

Index for this directory. The docs below define where agents are and are
not permitted to create files without explicit user permission.

| Doc | Covers |
|---|---|
| [POLICY.md](./POLICY.md) | Guarded paths, the allowed-additions escape hatch, init-time analysis, and the pre-commit enforcement mechanism |

The on-demand skill at `.claude/skills/file-placement-policy/SKILL.md`
is the condensed reference agents load at the start of a session.

## Problem

AI agents can silently create files anywhere in a project. Over time this
leads to a cluttered root, unexpected directories in `docs/`, and stale
config files that nobody owns. Once the pollution accumulates, it's hard
to tell what belongs.

## Solution

1. At `agentharness init`, analyze the existing structure and generate
   `.agentharness-guarded-paths.json`.
2. Agents check this file before creating any new file (via the skill).
3. A pre-commit hook blocks commits that add guarded files without permission.
4. For new projects, the analyzer recommends a structure the user can accept.
