---
name: multi-agent-coordination
description: Protocol, lock-file format, and worktree isolation rules for coordinating concurrent agent sessions on the same repository. Use when two or more agents may work on the same codebase simultaneously.
complexity: low
scope: [all]
---

# Multi-Agent Coordination

## The problem

Two agent sessions running concurrently in the same repository will fight
over the same working tree, `git stash`, index, and branch HEAD. The result
is corrupted state and lost work.

## The solution: per-feature lock files + worktrees

Each agent **locks** the feature it's working on by writing a small JSON file
to `.agentharness-locks/`. A second agent that wants to work on the same
feature reads the lock, detects the conflict, and either:

- **Waits** — if the first agent will finish soon.
- **Creates its own worktree** on a fresh branch — if parallel work is
  acceptable or expected.

---

## Lock file format

`.agentharness-locks/<feature-slug>.json`:

```json
{
  "agent_id":       "3f2a1c8d-...",
  "feature":        "add-user-auth",
  "branch":         "feat/user-auth",
  "worktree":       ".worktrees/feat-user-auth",
  "started_at":     "2026-07-14T10:00:00Z",
  "pid":              12345,
  "pid_started_at":   1784023200,
  "lease_expires_at": "2026-07-14T14:00:00Z"
}
```

| Field | Purpose |
|---|---|
| `agent_id` | Random UUID — uniquely identifies the agent session |
| `feature` | Human-readable description (becomes the lock file name slug) |
| `branch` | The branch this agent is using |
| `worktree` | Path to the worktree, or `null` if using the main checkout |
| `started_at` | ISO 8601 UTC timestamp the lock was acquired |
| `pid` | OS process ID of the session's stable process — one of two liveness grants (see below). Defaults to `$PPID`; callers whose parent does not outlive the session must pass `AGENT_LOCK_PID` explicitly |
| `pid_started_at` | Epoch seconds `pid` itself started, captured at acquire time — used to detect pid reuse (see below); `null`/absent on locks written before this field existed or when undeterminable, in which case detection falls back to `pid` liveness alone |
| `lease_expires_at` | ISO 8601 UTC expiry — the second liveness grant, so a lock survives its acquiring process exiting. Default TTL 4h (`AGENT_LOCK_LEASE_SECONDS`), extended by `renew`; absent on locks written before this field existed, in which case detection falls back to `pid` liveness alone |

---

## Stale lock detection

A lock has **two independent liveness grants**, and is stale only when
**both** are absent:

1. **Live owner pid** — `pid` still refers to the running process that
   acquired the lock (not one that merely reused the number).
2. **Valid lease** — `lease_expires_at` is still in the future.

Deriving liveness from `pid` alone was wrong in both directions.

**Too slow to expire.** A `pid` can answer `kill -0`
while belonging to a completely different, unrelated process — the OS
reused the number after the original owner exited. Observed in practice
([issue #148](https://github.com/andr-ca/agentharness/issues/148)): a
lock for a branch merged a week earlier still read as "live" because its
recorded `pid` had since been reassigned to an unrelated long-running
shell. So grant 1 requires more than `kill -0`: that pid's *current*
process-start time must still match `pid_started_at` — a mismatch means
the pid was reused, and the pid grant does not apply regardless of
`kill -0`'s answer.

**Too eager to expire.** The recorded `pid` also dies while the logical
session is very much alive — for clients that run each tool call in a
fresh process, and for *any* caller that ran `acquire` inside a command
substitution, where the recorded owner is a subshell that exits
immediately. Treating that as death made a live session's lock silently
vanish, letting a second session start overlapping work. Grant 2 (the
lease) covers exactly this case: the lock stays valid for its TTL
regardless of what happened to the acquiring process, and `renew`
extends it for a session that outlives the default.

A genuinely crashed owner is still recoverable — its pid is dead and its
lease eventually runs out — just not instantly. That delay is the
deliberate trade: bounded recovery time in exchange for never silently
expiring a live session.

**Scope: locks are repo-wide, the session marker is per-checkout.** The
lock store resolves from the repository's git common directory, which is
the same absolute path from the primary checkout and every linked
worktree — so one store serves them all. Deriving it from the current
checkout instead made locks invisible across worktrees, letting two
agents each see the same branch as free; worktree isolation is meant to
prevent working-tree collisions, not to hide the state that coordinates
them. The session marker stays beside the current checkout by design.

**Ownership** (as distinct from liveness) is provable three ways: a
matching `AGENTHARNESS_AGENT_ID`, an ancestor-pid match, or membership
in the per-checkout session marker `.agentharness-locks/.session-ids`
that `acquire` writes. The third exists because hook processes run in
their own process tree and do not inherit an `AGENTHARNESS_AGENT_ID`
exported inline by a single agent tool call.

When a stale lock is detected, it must be deleted before a new one is
created — do not skip detection and overwrite silently.

---

## Acquiring a lock

```bash
# agent-lock.sh acquire <feature> <branch> [worktree]
AGENT_LOCK_PID=<stable-session-pid> tools/agent-lock.sh acquire "add-user-auth" "feat/user-auth"
```

Steps:
1. Compute `feature-slug` = lowercase, hyphens, max 40 chars + 8-char hash suffix.
2. Check `.agentharness-locks/<slug>.json` — if it exists and is not stale:
   - Print the existing lock (feature, branch, worktree).
   - Exit non-zero with: `LOCKED: feature already being worked on`.
3. Write the lock file atomically (`mktemp` + `mv`), recording `pid`,
   `pid_started_at`, and `lease_expires_at`.
4. Record `agent_id` in the per-checkout session marker.
5. Exit 0.

Never capture the printed id with command substitution
(`ID="$(… acquire …)"`) — that records the substitution subshell as the
owner process, and it exits immediately. Read the id from the output and
export it as `AGENTHARNESS_AGENT_ID`.

---

## Renewing a lease

```bash
tools/agent-lock.sh renew "add-user-auth" "$AGENT_ID"
```

Extends `lease_expires_at` by another TTL. Requires a matching
`agent_id` (falls back to `$AGENTHARNESS_AGENT_ID`), so one session
cannot extend another's lease. Only needed when a session outlives the
TTL without a live owner pid.

---

## Releasing a lock

```bash
tools/agent-lock.sh release "add-user-auth" "$AGENT_ID"
```

Steps:
1. Find `.agentharness-locks/<slug>.json`.
2. Verify `agent_id` matches `$AGENT_ID` — don't release someone else's lock.
3. Delete the file.
4. Exit 0.

---

## What to do when a lock exists

```
LOCKED: 'add-user-auth' is being worked on by agent 3f2a1c8d on branch feat/user-auth.

Options:
  1. Wait for that agent to finish and release the lock.
  2. Create your own branch and worktree:
       git worktree add -b feat/user-auth-agent-2 .worktrees/user-auth-2 main
```

The suggested branch name: `feat/<slug>-agent-<timestamp>`.

---

## Worktree isolation rules

When running parallel agents, each agent **must** have its own worktree:

```bash
# Agent 1 — primary branch
git worktree add -b feat/user-auth .worktrees/user-auth main

# Agent 2 — parallel branch
git worktree add -b feat/user-auth-2 .worktrees/user-auth-2 main
```

**Never** share a worktree between agents. Git's index, `ORIG_HEAD`, and
`MERGE_HEAD` files are per-worktree — two agents in the same worktree will
corrupt each other's state.

---

## `.agentharness-locks/` in `.gitignore`

Lock files are operational state, not committed history. Add to `.gitignore`:

```gitignore
.agentharness-locks/
```

---

## Cleanup

Stale locks are auto-removed on `acquire` and `list` commands. To manually
clean all stale locks:

```bash
tools/agent-lock.sh clean
```

---

## Enforcement (added 2026-07-16)

**This describes agentharness's own repo.** `tools/agent-lock.sh` is not
installed into consumer projects by `harness-link.sh` — none of the
enforcement layers below apply to a consumer install unless the tool has
been added there by hand. Check `[ -x tools/agent-lock.sh ]` first.

The protocol above is advisory on its own — and stayed unused when two
sessions collided on one branch on 2026-07-16 (different feature names,
same remote branch). Three enforcement layers now back it:

1. **Remote (zero cooperation needed):** a GitHub ruleset
   (`no-force-push-any-branch`) rejects non-fast-forward pushes on every
   branch, with no bypass actors. A session that would have clobbered
   another's commits gets its push rejected and must fetch + rebase.
2. **`pre-push` hook:** for each branch being pushed,
   `tools/agent-lock.sh check-branch <branch>` runs before any test
   suite. A live lock held by a different session blocks the push.
   `AGENTHARNESS_LOCK_BYPASS=1` overrides (emergencies only).
3. **Claude Code `PreToolUse` hook**
   (`.github/hooks/claude-push-lock-guard.sh`, wired in
   `.claude/settings.json`): blocks a `git push` Bash call at the agent
   layer, before git even runs — this fires whether or not the session
   ever loaded this skill. A `SessionStart` hook also prints active
   locks and worktrees so every session starts aware of its neighbors.

**Branch is the unit of exclusion for pushes.** `check-branch` matches
locks by their `branch` field, not the feature name — the contended
resource is the remote ref. Ownership is recognized by
`AGENTHARNESS_AGENT_ID` matching the lock's `agent_id`, or by the lock's
recorded `pid` being an ancestor of the checking process (so a session
recognizes its own lock without exporting anything).

---

## Integration with the branching skill

See `.agents/skills/branching/SKILL.md` for the full branch and worktree
naming conventions. Multi-agent lock naming follows the same `feat/<slug>`
pattern.
