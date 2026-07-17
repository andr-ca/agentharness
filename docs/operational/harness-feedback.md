---
date: 2026-07-17
topic: operational
purpose: Dated log of harness friction found while using agentharness itself, per the harness-feedback skill
---

# Harness Feedback Log

Friction found while *using* this harness, recorded per
`.claude/skills/harness-feedback/SKILL.md`: what happened → root cause →
impact → what agentharness should change → corrective action taken. In
consuming projects this file lives at the same path; entries here are the
self-hosted (dogfood) case.

## 2026-07-17 – content-quality scan descends into `.claude/worktrees/`, false-failing the completion gate

**What happened:** Running `tools/check-completion.sh` before a commit on
PR #82, the content-quality gate failed with 12 mandate-restatement errors,
all inside `.claude/worktrees/agent-*/docs/operational/reviews/` — stale
checkouts left by finished subagent sessions, not current repo content.
The change under test was clean and CI was green throughout.

**Root cause:** Same failure class as launch-readiness item E9: that fix
pruned `.worktrees/` from the markdown scan in
`tools/verify-content-quality.py`, but Claude Code's agent worktrees live
under `.claude/worktrees/`, which the prune didn't cover.

**Impact:** The Stop-hook completion gate blocks on false failures whenever
a finished subagent worktree lingers; a commit was pushed with the gate red
(CI authoritative for this class), which is a bad pattern to normalize.

**What agentharness should change:** Exclude any `worktrees` path component
and `node_modules` from the markdown scan (the launch-plan addendum already
flagged nested `.kilo/node_modules`/`.opencode/node_modules`).

**Corrective action taken:** Removed the three stale agent worktrees
(`git worktree remove`), turning the gate green immediately; extended the
scanner exclusion in the same PR as this entry. Logged upstream as
[#83](https://github.com/andr-ca/agentharness/issues/83).
