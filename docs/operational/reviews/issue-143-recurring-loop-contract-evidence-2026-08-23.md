---
date: 2026-08-23
status: completed
topic: research
purpose: Post-hoc evidence test for issue #143's proposed scheduler-neutral loop contract, against this repo's two real recurring loops
related-harness: .github/dependabot.yml, .github/workflows/link-check-scheduled.yml
---

# Issue #143 — does the proposed loop contract fit two loops we already run?

## Why this exists

Issue #143 proposes a shared contract for recurring maintenance loops
(invariant, signal, proof, authority, durable state, retry/escalation,
human-attention budget, retirement), but every product-owner pass on it
(2026-07-22 through 2026-08-19) deferred building it: zero demonstrated
reuse, a contract abstracted from hypothetical loops is speculation. The
2026-08-18 review proposed a cheaper evidence path than waiting for a
dogfood program — write a post-hoc contract for the two recurring loops
this repo *already* runs (Dependabot, the scheduled link check) and see
if the vocabulary fits without stretching. This is that one-pager,
committed to on 2026-08-22's product-owner pass.

**This is not a new pattern doc.** It's a test of the proposed shape
against real instances. `patterns/` gets a new entry only if this fits.

## Loop 1: Dependabot (`.github/dependabot.yml`)

| Field | Value |
|---|---|
| **Invariant** | GitHub Actions dependencies pinned in workflow files stay current with upstream releases. |
| **Signal** | Weekly schedule (`interval: "weekly"`) — GitHub's own scheduler, not this repo's. |
| **Proof** | The PR Dependabot opens: a diff plus its own changelog/release-notes summary. This repo's CI (`ci.yml`) then re-runs against the bumped dependency — the proof that the invariant still holds *after* the change, not just that a PR exists. |
| **Authority** | Scoped to opening PRs only. No merge authority — every Dependabot PR goes through the same review/merge path as a human-authored one (this repo's branch protection makes no exception for it). |
| **Durable state** | None this repo owns. GitHub's Dependabot service tracks what it last proposed; this repo has no local state file. |
| **Retry / escalation** | Implicit: if a Dependabot PR goes stale (superseded by a newer version), Dependabot itself closes it and opens a fresh one next week. No retry budget is visible to this repo — it's GitHub's internals. |
| **Human-attention budget** | One PR review per update, at most weekly per ecosystem. Currently one ecosystem (`github-actions`), so worst case is a handful of PRs/week. |
| **Retirement** | Not applicable — this is a standing loop, not a bounded task. Retirement would mean removing the `dependabot.yml` entry, which happens if the ecosystem is dropped entirely (e.g., this repo's own comment notes a `gomod` entry was pre-removed because the manifest doesn't exist yet). |

**Fit:** Six of eight fields map cleanly with no stretching. Durable
state and retry/escalation are the two that don't — both are true here
because GitHub owns that half of the loop, not this repo. That's a real
data point: **the contract's fields assume the repo hosting the contract
also owns the loop's state and retry logic.** Dependabot is a
counter-example — a loop this repo depends on but only half-owns.

## Loop 2: Scheduled link check (`.github/workflows/link-check-scheduled.yml`)

| Field | Value |
|---|---|
| **Invariant** | Every external URL referenced in this repo's markdown resolves (not 404/dead), decoupled from the PR-blocking offline check in `ci.yml` (which only verifies path existence, per that workflow's own comment, so a flaky third-party host never blocks a merge). |
| **Signal** | `cron: "0 6 * * 1"` (weekly, Monday 06:00 UTC) or `workflow_dispatch` for on-demand runs after editing links. |
| **Proof** | `lychee-action`'s own pass/fail report; `fail: true` makes a broken link a failed run, visible in the Actions tab — no separate proof artifact beyond the run's own conclusion. |
| **Authority** | Read-only (`permissions: contents: read`). It can only fail a check; it cannot open a PR, comment, or modify anything. Weakest-authority loop in the repo by design. |
| **Durable state** | None. Each run is a fresh, stateless scan — no memory of which links were broken last week vs. this week. |
| **Retry / escalation** | None built in. A failed run is a failed GitHub Actions run; escalation is "someone notices the red X," which depends entirely on someone watching the Actions tab or the repo's notification settings. There is no retry-with-backoff and no explicit human ping. |
| **Human-attention budget** | Zero, until something breaks — then unbounded (a human has to find and fix every reported dead link, no batching or dedup across runs). |
| **Retirement** | Same as Dependabot: standing loop, retires only if the workflow file is deleted. |

**Fit:** Invariant, signal, proof, authority, and durable-state-as-absent
all map cleanly. **Escalation is the field that doesn't fit at all** —
there is no mechanism in this loop beyond "a human happens to look."
That's a second real data point, different from Dependabot's: this
contract field assumes an active escalation path exists, and the
cheapest loops in a repo often don't have one — they rely on ambient
visibility (a red CI badge) instead.

## What this settles

Running both loops through the vocabulary **on paper** (not live-driven,
per the committed scope: this is the evidence pass, not the dogfood
pass) surfaces two consistent gaps rather than a clean fit or a clean
miss:

1. **Durable state and retry/escalation are the two fields that don't
   transfer as-written.** Both loops here are cheap specifically because
   they don't own state or retry logic themselves — they delegate to
   GitHub's own scheduler/service layer and to ambient human attention.
   A contract written from these two instances alone would either have
   to make those fields optional, or acknowledge a class of loop
   ("thin wrapper around a platform-native scheduler") that the fuller
   contract doesn't describe well.
2. **Everything else — invariant, signal, proof, authority, human-attention
   budget, retirement — fits both loops without stretching.** That's five
   of eight fields, not zero.

**Duplicate-delivery and nothing-to-do, on paper:**
- *Duplicate delivery*: neither loop can double-fire in a way that causes
  harm. Dependabot's own dedup (closing superseded PRs) handles it
  upstream; the link checker is idempotent by construction (a second run
  the same week just reports the same result again, no side effect).
- *Nothing-to-do*: both loops handle this natively — Dependabot opens no
  PR if nothing's outdated; the link checker's run is green if nothing's
  broken. Neither needs contract-level help to stay quiet when there's
  nothing to report.

## Disposition

Per the 2026-08-22 product-owner ruling's decision rule: the vocabulary
fits **most but not cleanly all** of both loops. Six of eight fields
(invariant, signal, proof, authority, human-attention budget,
retirement) generalize without stretching across two structurally
different loops (one has write authority and upstream state, one is
read-only and stateless) — that's real signal, not a coincidence of
picking similar loops. Two fields (durable state, retry/escalation)
don't transfer because both loops here delegate that half to a platform
service rather than owning it locally.

**Recommendation: re-scope, don't build the original eight-field
contract.** The evidence supports a smaller contract — the six fields
that actually generalized — plus an explicit note that durable-state and
retry/escalation are loop-specific concerns to design when a loop
*does* own them locally (neither existing loop needs that decision made
generically). Building the full eight-field version now would encode
two fields nothing in this repo has actually exercised. This is a
call for the next product-owner pass on #143, not a decision made here —
this document is the evidence, not the ruling.
