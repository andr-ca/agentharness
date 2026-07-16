---
date: 2026-07-16
status: in-progress
topic: planning
purpose: Sequenced readiness plan for the repo's first deliberate public-attention moment — an external article and social post will link here
related-harness: docs/operational/reviews/fable-gpt5-sol-disposition-2026-07-14.md
---

# Public-Launch Readiness Plan (2026-07-16)

## Overview

An external article on why coding agents need a harness, with an
accompanying social post, will link to this repository. That is a
different bar than merely being public (this repo has been public since
2026-07-11): readers will arrive cold, skim the README for under a
minute, and the skeptical minority will check whether the repo's own
audit trail contradicts its pitch. This plan sequences the work needed
before that link goes out.

Every status below was **re-verified against the tree on 2026-07-16**
(branch `docs/public-launch-readiness`, base `2d9fd41`) — not copied
from prior status documents.

## Verified current state

Findings labeled F-xx come from
[fable-gpt5-sol-disposition-2026-07-14.md](../reviews/fable-gpt5-sol-disposition-2026-07-14.md).

| Finding | Status at HEAD | Evidence (2026-07-16) |
|---|---|---|
| F-01 adapter drift | ✅ Closed (manually) | `CLAUDE.md` last edited 2026-07-15; `AGENTS.md`/`GEMINI.md` regenerated 2026-07-16 — currently in sync. No automation guarding recurrence. |
| F-02 committing-skill contradiction | ❌ Open | `.claude/skills/committing/SKILL.md` (lines 46–52) still mandates "commit → push → PR. Don't stop at the commit," contradicting the opt-in publish-authority model. Safety-relevant; ships to every consumer. |
| F-03 destructive `generate-clients` | ❌ Open | `cmd_generate_clients` (`tools/setup/harness-link.sh`) still has no existence check, `--force`, backup, or state record. |
| F-04 npm durable copy over-broad | ❌ Open | `copy_npm_durable_source` still tars everything except `.git` and the durable dir — untracked `.env*` would be copied into a consumer. |
| F-05 hooks path not restored on uninstall | ❌ Open | Zero occurrences of `previous_hooks_path` in `harness-link.sh`. |
| F-06 stale hand-written status | ⚠️ Stale | `docs/STATUS.md` says "last verified 2026-07-13" — that predates the Tier-2/3 skill batches, the bootstrap-policy core, and the completion gate. |
| F-07 review-loop archive | ❌ Open | `docs/operational/reviews/` is flat — 15 files, no dated archive dirs. |
| F-08 external evidence | ❌ Open | `docs/KNOWN_LIMITATIONS.md` remains accurate: no real-world dogfood, no live non-Claude session, no eval run. |

**Also fixed while verifying** (dev environment, not repo content): this
checkout's local git config carried leaked test state — `core.bare=true`,
`core.hooksPath=someone/else/changed/this`, and a stale
`submodule..agentharness.url` pointing into a deleted `/tmp` directory —
which had left the working tree frozen at a pre-PR-#55 state while
`main`'s ref advanced underneath it. Restored with `core.bare=false`,
`core.hooksPath=.github/hooks`, removing the stale submodule section,
and `git checkout -- .`. This is the F-05 failure class manifesting in
the dev checkout itself; treat it as live evidence for Workstream A, and
consider a test-infrastructure guard asserting the bats suites never
mutate the enclosing repo's config.

## Workstream A — close the open P0s (blocking)

The repo's own filed reviews call F-02–F-05 release blockers, one of
them safety-relevant. A reader who follows the audit trail will find
them; "fixed, or honestly re-dispositioned with rationale" is the bar.

| Item | Action | Est. |
|---|---|---|
| F-02 | Rewrite committing skill to the verify-and-stage default + publish-authority reference; regenerate `.cursor/rules/committing.mdc` and `.agents/skills/committing/` | 30 min |
| F-03 | `generate-clients`: refuse when target exists and isn't harness-generated; add `--force` / `--dry-run`; record outputs in state | 2 h |
| F-04 | npm durable copy: allowlist-based copy (or reject unrecognized sources); always exclude `.env*`, VCS metadata, caches; tests | 1 h |
| F-05 | Persist `previous_hooks_path` in state; restore on uninstall; warn on post-install user change; tests | 1 h |
| Follow-up | Update the 2026-07-14 disposition doc's per-item statuses to match | 15 min |

## Workstream B — front door (blocking, ~1 h)

- **GitHub repo description** — still the pre-product placeholder
  ("My handpicked harnesses…"); replace with the README's actual
  one-liner.
- **Topics** — currently none; add (e.g. `ai-agents`, `claude-code`,
  `coding-agents`, `agent-skills`, `developer-tools`).
- **Homepage** — set (owner's site).
- **README top restructure** — first screen should carry: the pitch
  paragraph, then the three distinctive governance mechanisms (opt-in
  publish authority, enforced completion gate, review/merge mandates),
  then the `docs/DEMO.md` link — before the compatibility matrices and
  caveat blocks that currently dominate the first scroll.
- **Naming** — one explicit line that the repo is `agentharness` and the
  npm package is `agentharness-toolkit`.

## Workstream C — doc-accuracy sweep (blocking, ~1–2 h)

- Re-verify `docs/STATUS.md` row by row; bump its "last verified" date.
- Re-verify `docs/KNOWN_LIMITATIONS.md` against the tree.
- Optional but recommended (F-07): archive completed review cycles under
  dated directories so `docs/operational/` reads as history rather than
  churn to a first-time visitor.

## Workstream D — external evidence (highest value, scheduled)

Execute [planning/DOGFOODING.md](./DOGFOODING.md) against at least one
real, non-fixture project (owner has candidates lined up; target:
before 2026-07-19 weekend is over).

- A **public** target is preferred for this launch: it produces
  linkable evidence (a real repo, a real commit installing the harness).
- A second, **private**, different-stack target adds signal per
  DOGFOODING.md's P2-02 note without needing a public link.
- Record findings in DOGFOODING.md's tracking table; update
  `KNOWN_LIMITATIONS.md`'s "no real-world dogfood" bullet accordingly.

## Sequencing and definition of done

A → C → B (all doable in a day, in that order — fixes first, then make
the docs describe the fixed state, then polish the surface) → D
(weekend) → article links in.

Done means: every ❌ row above is ✅ or re-dispositioned with written
rationale; STATUS/KNOWN_LIMITATIONS re-verified at a current commit;
repo metadata updated; at least one dogfood row recorded.

## Out of scope (deliberate)

- **F-09** (CLAUDE.md always-on token budget) and **F-10**
  (ARCHITECTURE.md rewrite) — real items, not launch-gating; they stay
  on the disposition backlog.
- **Funded eval runs** (P2) — post-launch.
- **The article itself** — external content, drafted and maintained
  outside the repo in the gitignored local `media/` workspace.
