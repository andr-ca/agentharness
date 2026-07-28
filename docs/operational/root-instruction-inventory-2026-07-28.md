---
date: 2026-07-28
topic: operational
purpose: Evidence for issue #175 — classify root agent instructions as constitution/router/procedure, measure context cost, and identify which sections can safely be thinned
---

# Root Instruction Inventory

Evidence gathering for [#175](https://github.com/andr-ca/agentharness/issues/175),
which proposes reducing `CLAUDE.md` to a "thin constitution plus task
router". **This document moves nothing and changes no policy.** It
measures what is there, classifies it, and reports which sections a
thinning pass could touch safely — which turns out not to be the ones a
line count would suggest.

## Context cost

| File | Lines | ~Tokens |
|---|---:|---:|
| `CLAUDE.md` (source) | 353 | ~4,930 |
| `AGENTS.md` (generated) | 411 | ~7,665 |
| `GEMINI.md` (generated) | 417 | ~7,729 |
| `.github/copilot-instructions.md` (generated) | 416 | ~7,713 |
| `.kilo/rules/agentharness.md` (generated) | 414 | ~7,686 |

The generated clients are **~55% larger than the source** — they inline
material `CLAUDE.md` reaches by reference. Any budget must be set on the
generated output, not the source, or it will measure the wrong thing.
This confirms #175's "validate the generated outputs, not just the source
file" requirement.

## Section inventory

| Lines | ~Tok | Section | Class |
|---:|---:|---|---|
| 6 | 58 | (preamble / router intro) | router |
| 142 | 2,189 | 🤖 Agent Workflow Completion | **procedure** |
| 20 | 286 | └ Publish authority | constitution |
| 59 | 736 | 📁 File Placement | procedure |
| 47 | 612 | 🔍 Agent Recommendation Assessment | constitution |
| 25 | 246 | 📋 Completion Gate | router |
| 7 | 72 | What This Repo Is | router |
| 13 | 146 | Where To Look | router |
| 29 | 524 | Rules That Apply Regardless | constitution |
| 5 | 56 | Operational Documents | router |

**Agent Workflow Completion alone is 40% of the lines and 44% of the
tokens.** It is the only section large enough for thinning to matter, so
it is where the proposal's risk concentrates.

## The finding that should drive the decision

Sections are not equally safe to move, and **size does not predict
safety**. What predicts it is whether a mechanical gate enforces the same
rule when the prose isn't read:

| Rule | Mechanical enforcement | Safe to compress? |
|---|---|---|
| Completion gate | `tools/check-completion.sh` + `Stop` hook | **Yes** — gate still fires |
| File placement | `tools/check-file-placement.sh` pre-commit | **Yes** |
| Trunk protection / no force-push | GitHub ruleset (no bypass) | **Yes** |
| Lock protocol | pre-push hook + `PreToolUse` guard | **Yes** |
| Writes outside the repo | `claude-outside-repo-write-guard.sh` | Partly — hook covers `Write`/`Edit` only, not `Bash` redirects |
| Publish authority | `.agentharness-authority.json` + pre-push gate | Partly — contract is opt-in |
| **PR-merge checklist** (~60 lines) | **none** | **No** |
| **CI-wait / "merged ≠ confirmed working"** | **none** | **No** |
| **Recommendation Assessment** | **none** | **No** |

`tools/safe-pr-merge.sh` implements the merge checklist, but **nothing
requires its use** — there is no hook on `gh pr merge` (verified against
`.claude/settings.json` and `.github/hooks/`). The agent runs it because
`CLAUDE.md` says to. That prose *is* the enforcement.

So the largest section is also the least safe to move, and a
line-count-driven thinning pass would go straight at it.

## Direct evidence from the 2026-07-28 session

That session is a natural experiment, because the prose-only rules were
load-bearing and can be traced to specific outcomes:

- The **PR-merge checklist** caused three merges to block on unanswered
  review comments. Addressing them surfaced two real defects in
  `safe-pr-merge.sh` (a reply check that could never pass on a
  bot-authored PR; a strategy-flag collision) and one in `agent-lock.sh`
  (an unvalidated env override that leaked the mutex and permanently
  deadlocked a feature). None of these had a failing test; all three were
  found because the checklist forced a reply to each comment.
- The **"merged ≠ confirmed working"** rule is why the
  `actions/github-script` v9 bump got a live webhook test. CI was green
  and static review was clean; only the live run confirmed the
  `issues:`-triggered workflow still functioned.
- The **verify-before-acting** rule in the same section is why two of
  five automated review findings were correctly rejected — one would have
  reintroduced a bash 3.2 `set -u` bug.

Each of those is a case where a compressed pointer ("follow the merge
checklist") would plausibly have been followed *less* literally.

## Recommendation

1. **Adopt a budget on generated output**, not the source — ~7,700 tokens
   is the number to manage.
2. **Compress only mechanically-backed sections.** Completion gate, file
   placement, trunk protection, and the lock protocol can shrink to a
   rule plus a pointer, because the hook still fires if the pointer is
   ignored. Estimated saving: modest, and that is the honest result.
3. **Do not move the prose-only sections** — PR-merge checklist, CI-wait,
   Recommendation Assessment — without either (a) a mechanical gate that
   replaces the prose, or (b) representative cross-client eval evidence
   showing compliance is unchanged.
4. **The higher-value alternative to thinning is gating.** Every section
   in the "No" column could be moved to the "Yes" column by adding
   enforcement. A `PreToolUse` hook on `gh pr merge` that requires
   `safe-pr-merge.sh` would make ~60 lines compressible *and* close the
   gap where an agent skips the checklist entirely. That is a smaller,
   testable change than a router redesign, and it attacks the same
   context cost from the safe end.

## What this does not establish

- Whether compression actually degrades compliance — that needs P2-03
  baseline/treatment runs, and `invoke_agent_via_api` is still
  `NotImplementedError`, so no real sessions can be scored.
- Whether generated-client parity holds after any move.
- Token counts here are `chars / 4` approximations, adequate for relative
  comparison, not for a hard budget threshold.
