---
description: Comprehensive git branching strategy, prefixes, worktrees, and gitignore guidelines
applyTo: all projects using agentharness
---

# Branching Strategy

Creating branches, rebasing, resolving conflicts, and worktree mechanics
are standard Git — see the [Git docs](https://git-scm.com/doc) and
[`git-worktree`](https://git-scm.com/docs/git-worktree) for those. Below
are the conventions and rules this repo actually enforces.

## Core rule: never commit to trunk

Trunk branches (`main`, `master`, `trunk`, `develop`, `release/*`) only
get changes via PR — create a feature branch, get it reviewed, merge
back. This is enforced by `.github/hooks/prevent-trunk-commit` (see
`.github/hooks/README.md`), not just a convention to remember.

Note `release/*` is in that list: it means a long-lived release *line*
that receives changes by PR, not a working branch. Preparing a release —
moving the changelog, bumping the version — is ordinary work and belongs
on `chore/release-vX.Y.Z`. Naming it `release/v1.2.3` is the intuitive
choice and gets the commit refused, which is correct but surprising.

## Branch naming convention

Format: `{type}/{description}`, lowercase, hyphens not underscores.

| Type | Purpose | Example |
|------|---------|---------|
| `feature/` | New feature or enhancement | `feature/user-authentication` |
| `fix/` | Bug fix | `fix/email-validation-crash` |
| `refactor/` | Code refactoring (no behavior change) | `refactor/simplify-user-service` |
| `test/` | Testing improvements | `test/add-integration-tests` |
| `docs/` | Documentation changes | `docs/update-readme` |
| `chore/` | Maintenance, deps, config | `chore/upgrade-dependencies` |
| `perf/` | Performance improvement | `perf/optimize-query-caching` |
| `ci/` | CI/CD changes | `ci/add-coverage-reporting` |
| `wip/` | Work in progress (don't merge!) | `wip/exploring-new-approach` |

## Delete branches once they're merged

A merged branch has nothing left to give — its content is in trunk,
permanently reachable through whatever the merge produced there (a
merge commit for `--merge`, a single squashed commit for `--squash`, or
the replayed commits themselves for `--rebase`). Keeping the branch
around adds nothing and costs a little: `git branch -r`/`git fetch
--prune` noise,
one more thing a future cleanup has to re-verify is actually safe to
remove, and no signal left behind for which merged branches were
deliberately kept for a reason (there isn't one) versus simply never
cleaned up.

A repo audit on 2026-08-19 found 24 branches sitting on `origin` for
already-merged or already-superseded PRs, spanning weeks — none kept on
purpose, all just never deleted. Two things now close that gap:

- **This repo's GitHub setting `delete_branch_on_merge` is enabled** —
  merging a PR through the GitHub UI, `gh pr merge`, or
  `tools/safe-pr-merge.sh` all delete the head branch automatically.
- **`tools/safe-pr-merge.sh` also defaults to passing `--delete-branch`
  itself**, so the behavior travels with the script into any project
  that adopts this harness, independent of that project's own repo
  settings. Pass `--delete-branch=false` on a specific merge if you
  have a real reason to keep that one branch around.

If you're cleaning up branches that predate this convention: verify
each one is actually safe first (merged into trunk, or its PR closed in
favor of a since-merged replacement, or fully redundant with an
existing tag) — don't blanket-delete on the assumption that "old" means
"safe." `git merge-base --is-ancestor` misses squash-merged branches
(diff against trunk directly instead, or check the PR's `mergedAt`
state); a closed-but-unmerged PR needs its own closing comment or diff
checked for where its content actually landed.

## Worktrees

A worktree (`git worktree add`) gives you a second working directory
backed by the same repository — multiple branches checked out at once,
sharing one object store, without a second clone. This repo defers the
generic mechanics to [`git-worktree`](https://git-scm.com/docs/git-worktree)
and documents only the decisions and the sharp edges.

### When they earn their keep

- Long-running tests or builds on one branch while you keep coding on
  another.
- Reviewing or bisecting a branch without stashing your in-progress work.
- **Parallel agent runs** — the highest-value case here: give each agent
  or task its own worktree under `.worktrees/{branch}` so concurrent runs
  never collide on a single working tree, index, or in-flight edit. One
  agent per worktree, one branch per worktree.

Skip them for a single quick edit; a branch switch is cheaper than the
directory bookkeeping.

### Conventions and the edges that bite

- **Keep them under `.worktrees/`** (one directory per branch), added to
  `.gitignore` — the one convention this repo adds on top of standard
  usage. The `.github/.gitignore.template` already ignores it.
- **One branch, one worktree.** Git refuses to check the same branch out
  in two worktrees at once, so a branch lives in exactly one place.
- **Config and hooks are shared by default.** Worktrees share the common
  `.git` directory, so `core.hooksPath`, remotes, and config apply to all
  of them unless you deliberately opt into per-worktree config
  (`extensions.worktreeConfig`). In practice the trunk-protection and
  pre-push hooks run in every worktree automatically — you won't
  *accidentally* bypass them by moving to one.
- **Remove via git.** `git worktree remove <dir>` when done, or
  `git worktree prune` if you deleted the directory by hand — never just
  `rm -rf` and walk away, or git keeps a stale registration.
  `git worktree list` shows what's currently registered.
- **Submodules init per worktree.** If you consume this harness in
  `--mode submodule`, a freshly-added worktree starts with an empty
  submodule — run `git submodule update --init` inside it before the
  harness's skills resolve there.

## .gitignore configuration

Don't hand-roll a `.gitignore` — copy the canonical, maintained template:

```bash
cp .github/.gitignore.template your-project/.gitignore
```

That file documents the policy notes: lock files (`package-lock.json`,
`go.sum`, …) and version-pin files (`.nvmrc`, `.python-version`, …) are
**committed**, not ignored, since they make builds reproducible. `.env`
is ignored; `.env.sample` (sanitized, no real secrets) is committed.

## Protecting secrets

Before pushing, check staged/unstaged diffs for common secret patterns:

```bash
git diff | grep -iE "password|api[_-]?key|secret|token"
git diff --cached | grep -iE "password|api[_-]?key|secret|token"
```

### If you accidentally committed secrets

**Act immediately — and rotate the secret regardless of whether history cleanup succeeds. A secret that touched git history must be treated as compromised.**

**Preferred: BFG Repo Cleaner** (`brew install bfg` or download the jar) — much faster and safer than `filter-branch`:

```bash
# 1. Clone a fresh mirror (BFG operates on a bare mirror clone, not your working copy)
git clone --mirror git@github.com:you/your-repo.git repo-mirror.git
cd repo-mirror.git

# 2. Delete the file by name from all of history
bfg --delete-files .env

# 3. Clean up and push the rewritten history to every branch
#
# agentharness:force-push-exception — purging a secret from history
# REQUIRES rewriting it, so this is the one place a force-push is correct.
# It will still be rejected until an admin temporarily disables the
# no-force-push-any-branch ruleset: do that immediately before this step
# and re-enable it immediately after. Discovering the block mid-incident
# is the worst possible time to learn about it.
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force

# 4. Everyone with a clone must re-clone or hard-reset — rewritten history
#    doesn't merge cleanly with old clones.
```

**Fallback (no BFG available): `git filter-repo`** (the modern, maintained
replacement for `filter-branch`, which is slow and easy to misuse):

```bash
# agentharness:force-push-exception — same as above: this rewrites
# history to purge a secret, and needs the ruleset temporarily disabled.
git filter-repo --path .env --invert-paths
git push --force
```

**Either way:**
1. Rotate the leaked secret immediately — assume it's compromised even after cleanup, since caches, forks, and CI logs may still hold the old history.
2. Notify anyone with a clone to re-clone rather than pull.
3. Add the file to `.gitignore` (or `!.env.sample`-style negation) so it can't be re-committed.

---

**See Also:** COMMITTING_GUIDELINES.md, CODING_GUIDELINES.md
