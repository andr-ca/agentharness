# Recurring Maintenance Loop Contract

A vocabulary for designing recurring maintenance work — dependency
updates, drift checks, freshness scans, and similar loops that run on
a schedule or on-demand rather than in response to a single request.
It is a **design contract, not a runtime**: nothing here prescribes a
scheduler, ships a daemon, or grants automatic merge authority. Use
whichever scheduler fits (a CI cron job, a local cron entry, a
platform-native service, or manual invocation) — the six fields below
describe the loop, not how it's triggered.

## Why six fields, not eight

An earlier draft of this contract proposed eight fields, including
**durable state** and **retry/escalation**. Tested against two real
recurring loops this repo already runs (a dependency-update bot and a
scheduled link checker — see
`docs/operational/reviews/issue-143-recurring-loop-contract-evidence-2026-08-23.md`
for the full evidence), those two fields didn't transfer: both loops
delegate that half of the problem to a platform-native scheduler
rather than owning it locally. That's not a gap in the evidence — it's
a real pattern. Many cheap recurring loops are cheap *because* they're
thin wrappers around a platform service that already owns state and
retry logic.

**Design durable state and retry/escalation explicitly, on your own,
the moment a loop you're building actually owns either** — for
example, a loop that tracks "which items were already handled" in its
own storage, or one that must survive a process restart mid-cycle.
Neither exists in either loop this contract was validated against, so
this doc doesn't prescribe a shape for them.

## The contract

| Field | Question it answers |
|---|---|
| **Invariant** | What condition is this loop maintaining? (e.g., "dependencies stay current with upstream releases") |
| **Signal** | What triggers a cycle — a schedule, an event, or manual invocation? |
| **Proof** | What evidence confirms the invariant still holds after the loop acts? (a passing CI re-run, a clean report — not just "a change was proposed") |
| **Authority** | What is this loop actually allowed to do? Read-only? Open a PR? Merge? Every step beyond the minimum needed is a step that needs its own justification. |
| **Human-attention budget** | What does a cycle cost a human, in the worst case? One PR review? An unbounded backlog if something breaks? |
| **Retirement** | How does this loop end? A standing loop retires when its trigger is removed; a bounded task retires on completion. Say which. |

## Worked shape (schedule-neutral)

```
Invariant:              <the condition being maintained>
Signal:                 <schedule | event | manual>
Proof:                  <what validates success after the loop acts>
Authority:              <read-only | opens PRs | merges | other — be exact>
Human-attention budget: <cost per cycle, worst case>
Retirement:             <standing (retires if the trigger is removed) | bounded (retires on completion)>
```

Fill in each line for your loop before building it. If you can't answer
one — especially **Proof** or **Authority** — that's a design gap worth
closing before the loop runs, not after.

## When this contract doesn't fit

If your loop genuinely owns durable state or retry/escalation locally
(not delegated to a platform), this six-field contract won't capture
that half of the design — extend it explicitly for your case rather
than stretching one of the six fields to cover it. If a loop turns out
not to fit this vocabulary at all, that's evidence this contract is
the wrong shape for that class of loop — worth a note in
`docs/operational/`, not a silent workaround.

## Non-goals

- No scheduler, daemon, or hosted control plane — bring your own trigger.
- No automatic-merge default — a loop's **Authority** field should say
  explicitly if it can merge, and that should be the exception, not
  the default.
- No generic agent-memory or state service — that's a different
  problem from designing one loop.

**See Also:** `patterns/agentic-loops/README.md` for the mechanics of
a single agentic tool-call loop (a different layer — that's about one
model turn calling tools, this is about a maintenance cycle that runs
repeatedly over time).
