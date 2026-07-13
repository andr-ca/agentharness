# Dogfooding Plan (P2-05 / P2-02)

**Status:** not started — this is the actionable plan, not a record of a
run. The single biggest open gap in the harness is that it has *no
real-world evidence*: it's exercised only by its own CI fixtures
(`examples/*-project/`), never pinned into a real project with a
different stack and a user other than the author. This doc makes that
gap executable so it isn't silently dropped between status snapshots.
See [ROADMAP.md](../../../ROADMAP.md) ("P2-05 (real dogfood) has no
target").

## Why this can't be faked

Fixtures prove the mechanics work; they can't surface *friction* — the
overrides a real team needs, the false positives that erode trust, the
context cost of loading the router every session, the features nobody
ends up using. Only real use over real time does that.

## Prerequisites

1. **A real, non-fixture repository.** Ideally *not* this session's
   author's own project — correlated blind spots are the whole reason
   fixtures aren't enough. At least one; two with different stacks is the
   P2-02 target.
2. **A pinned release**, not `main` — `harness-link.sh init --mode
   submodule` (pins via the submodule commit) or `--mode npm` against a
   fixed version, so the experience is reproducible and versioned.
3. **A real task in flight** in that repo — dogfooding during genuine
   work, not a throwaway hello-world.

## Procedure

1. Pick the repo and record its starting state (stack, size, existing
   `.gitignore`, any pre-existing agent config).
2. `harness-link.sh init <repo> --mode submodule --with-hook` (or npm).
   **Time it.** Note anything confusing or that needed `--force`.
3. Optionally `generate-clients <repo> --client <the tool you use>` and
   select a profile (`--profile`).
4. Use the repo normally for real work, with the harness active, for long
   enough that friction surfaces (days, not minutes).
5. Run `harness-link.sh doctor`/`audit --json` periodically; note any
   false alarms.
6. `harness-link.sh update` when a new release is cut. **Time it**; note
   whether the preview matched reality.
7. When done, `uninstall` and confirm the repo is clean.

## What to track (fill one row per dogfood target)

| Signal | What to record |
|---|---|
| Install time | Wall-clock for `init` to a working state |
| Overrides needed | Every repo-local override / `--force` / profile change |
| False positives | `doctor`/`audit`/enforcement alarms that were wrong |
| Update friction | Time + surprises for each `update` |
| Context cost | Rough token/size cost of the always-on router each session |
| Abandoned features | Anything installed but never actually used |
| Net verdict | Would this team keep it? Why / why not? |

## Where findings go

Record results in a dated status doc under
[`docs/operational/reviews/`](../reviews/) (e.g.
`dogfood-<repo>-<date>-status.md`), then feed the concrete gaps back into
[ROADMAP.md](../../../ROADMAP.md) as scoped items — the same
recommendation-assessment loop every other review here follows.
