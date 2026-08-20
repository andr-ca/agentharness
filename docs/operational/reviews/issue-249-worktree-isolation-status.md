# Issue #249 (Worktree Isolation Mandate Gap) — Status

**Timestamp:** 2026-08-20T06:07:22Z
**Source:** [#249](https://github.com/andr-ca/agentharness/issues/249) —
a dogfooding report filed from a consumer repo (breqy), via
`docs/operational/harness-feedback.md`'s upstream-filing path. An agent
session there started new feature work with `git checkout -b` directly
in a checkout that was ~100 files dirty from unrelated in-progress work,
despite the repo already using worktrees for other features and the
`branching` skill mentioning them as an option.
**PRs:** [#250](https://github.com/andr-ca/agentharness/pull/250)
(merged, merge commit `ca0d01c`) — includes a same-PR follow-up commit
fixing 3 Copilot review findings before merge.

## Why this document exists

Per `CLAUDE.md`'s Agent Recommendation Assessment mandate: scoped,
low-risk fixes get implemented directly and reported here; anything
larger (new tooling/subsystems) gets scoped and confirmed with the
operator first rather than folded into the same change.

## What #249 asked for (7 numbered recommendations)

| # | Recommendation | Status |
|---|---|---|
| 1 | Explicit precedence rule: dirty tree / unrelated branch → worktree is mandatory, not preferred | ✅ Fixed |
| 2 | Session-start checklist (`git status -sb && git branch -a && git worktree list`, isolate before TDD) | ✅ Fixed (folded into #1's rule rather than as a separate numbered checklist — the mandatory-condition check already covers the same ground) |
| 3 | New `pre-agent-edit`/completion-gate hook enforcing this mechanically | 🛑 Deferred — new enforcement tooling, not a doc/guidance gap; needs a scoping conversation, not a drive-by build |
| 4 | Strengthen `multi-agent-coordination`'s no-`agent-lock.sh` fallback so it can't be read as also waiving worktree isolation | ✅ Fixed |
| 5 | Resolve "confirm branch with user" vs "don't block on ask" ambiguity | ✅ Fixed — the new rule states this check runs on its own; the user is only asked when choosing between multiple *clean* strategies, never whether to isolate a dirty tree |
| 6 | Add a negative/positive exemplar to the `branching` skill | ✅ Fixed |
| 7 | Optional: ship a lightweight `tools/harness-session-start.sh` for consumers without the full lock tool | 🛑 Deferred — explicitly optional in the source issue; new tooling, same reasoning as #3 |

## What shipped (commit `90ff1fc`, follow-up `25327b2`)

- `branching` skill: dirty tree or unrelated branch now makes
  `git worktree add` mandatory before the first file edit, with the
  report's own ❌/✅ example (aligned to the repo's actual `feature/`
  branch prefix — Copilot's review caught my first draft using `feat/`,
  which doesn't match this same file's own naming table).
- `multi-agent-coordination` skill: the "no `agent-lock.sh`, fall back
  to plain git branch discipline" note now explicitly says that fallback
  is about coordinating with *other agents*, not license to skip
  worktree isolation on a dirty tree — including one's own in-progress
  changes, not just "someone else's" (a second Copilot finding, since
  the original wording under-scoped the warning).
- Regenerated `.cursor/rules/branching.mdc` and
  `.cursor/rules/multi-agent-coordination.mdc` so Cursor's full-body
  copies stay in sync; verified via the existing drift-check test.

## Caught by review, on this PR (all 6 total review comments replied to before merge)

Round 1 (3 comments) fixed the substance described above. Round 2 (3
more comments, after the round-1 push) caught wording precision issues
in that same fix: the `feat/`-vs-`feature/` branch-prefix mismatch, the
"someone else's" under-scoping, and a readability issue where the
pre-existing "skip it for a quick edit" line sat directly above the new
mandatory rule without a cross-reference, risking exactly the
misreading #249 reported. All fixed in the same PR before merge — see
PR #250's review thread for the verified-against-current-code replies.

## Deferred items — request for the operator

Items #3 (mechanical hook enforcement) and #7 (optional consumer
script) are real, reasonable follow-ups, not rejected — they're new
tooling decisions per the Recommendation Assessment mandate's "anything larger"
bar, so building them wasn't folded into this doc fix. Flagging on
[#249](https://github.com/andr-ca/agentharness/issues/249) for the
operator to scope explicitly if wanted; issue left open rather than
closed since its acceptance criteria aren't fully met yet.
