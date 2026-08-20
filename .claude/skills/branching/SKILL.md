---
name: branching
description: Use when creating a branch, naming it, deciding whether to use a worktree, or handling secrets accidentally committed to history — branch naming convention, trunk protection, and secrets-removal procedure.
metadata:
  type: skills
  complexity: low
---

# Branching

Full reference: `.github/BRANCHING_STRATEGY.md` (worktree deep-dive,
`.gitignore` policy, lifecycle walkthrough). This skill is the actionable
summary.

## The core rule

**Never commit directly to `main`/`master`/`trunk`/`develop`/`production`/
`release/*`.** Always: branch → commit → push → PR → merge. This repo
enforces it locally via `git config core.hooksPath .github/hooks`
(already set here) — don't rely on the admin bypass.

## Branch naming

`{type}/{description}`, lowercase, hyphens not underscores, short and
specific.

| Type | Purpose |
|---|---|
| `feature/` | New feature or enhancement |
| `fix/` | Bug fix |
| `refactor/` | No behavior change |
| `test/` | Testing improvements |
| `docs/` | Documentation only |
| `chore/` | Maintenance, deps, config |
| `perf/` | Performance improvement |
| `ci/` | CI/CD changes |

Good: `feature/user-authentication`, `fix/email-validation-crash`.
Bad: `update`, `Feature/UserAuth`, `fix_everything`.

## Worktrees

A worktree is a second working directory backed by the *same* repo, so
you can have several branches checked out at once without stashing or
re-cloning.

**Reach for one when:**

- Running long tests/builds on one branch while you keep coding another.
- Reviewing a PR branch without disturbing your in-progress work.
- **Running agents in parallel** — give each agent/task its own worktree
  so concurrent runs never fight over one working tree or index. This is
  the highest-value case for an agent harness.

Skip it for a single quick edit — a plain branch switch is cheaper.

**Mandatory, not a preference, before starting new feature/fix
implementation work** (not Q&A, not read-only investigation) when either
is true:

- `git status --porcelain` is non-empty (a dirty tree), or
- the current branch is unrelated to the task (someone else's topic
  branch, a `chore/*` tree, anything not already scoped to this work).

In that state, `git checkout -b` directly in the current checkout is
disallowed — isolate first:

```bash
git fetch origin
git worktree add -b feat/<short-name> .worktrees/feat-<short-name> origin/main
cd .worktrees/feat-<short-name>
```

❌ `git checkout -b feat/foo` on top of a `chore/*` branch carrying 100
modified files.
✅ `git worktree add -b feat/foo .worktrees/feat-foo origin/main`.

This check runs before the first file edit, on its own — it is not
something to ask the user about. A prompt like "let's build X"
authorizes starting the work, not skipping isolation. Only ask the user
when choosing between multiple *clean* strategies (e.g. a branch name);
never ask whether a dirty tree should be isolated — just do it.

**The rules that bite:**

- **One branch per worktree** — git refuses to check the same branch out
  in two worktrees at once.
- **Keep them in `.worktrees/{branch-name}/`** (gitignored — it's in
  `.github/.gitignore.template`), not scattered sibling directories.
- **Hooks are shared by default** — worktrees share one `.git` config and
  `core.hooksPath`, so trunk protection and the pre-push hook apply in
  all of them; you won't *accidentally* sidestep them by moving to a
  worktree (short of deliberately enabling per-worktree config).
- **Remove with git, not `rm -rf`** — `git worktree remove <dir>` (or
  `git worktree prune` if you already deleted it by hand), so git's
  bookkeeping stays consistent.

Full mechanics (submodule caveat, cleanup): `.github/BRANCHING_STRATEGY.md`.

## If a secret was committed

Act immediately — **rotate the secret regardless of whether history
cleanup succeeds**; treat anything that touched git history as
compromised.

1. Preferred: [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
   on a fresh mirror clone: `bfg --delete-files .env` then
   `git push --force`. See `.github/BRANCHING_STRATEGY.md` for the full
   command sequence.
2. Fallback: `git filter-repo --path .env --invert-paths` (the modern,
   maintained replacement for `filter-branch`).
3. Rotate the secret. Tell everyone with a clone to re-clone, not pull.
