---
date: 2026-07-29
topic: operational
purpose: Analysis and build recommendation for cohesive context management, assessing the Context Plane epic (#194) against what the repo already has
---

# Context Management: Analysis and Recommendation

Requested assessment of how to build cohesive, complete context
management, evaluating the Context Plane epic ([#194](https://github.com/andr-ca/agentharness/issues/194))
and its six slices ([#195](https://github.com/andr-ca/agentharness/issues/195)–[#200](https://github.com/andr-ca/agentharness/issues/200)).

**Bottom line:** the epic's central idea is right and worth building. Its
*sequencing* is backwards, and one slice should not be built at all. The
biggest risk is not under-building — it is that a context budget,
naively enforced, would delete the guidance that currently does the most
work.

---

## 1. Not all six functions are equally unbuilt

The epic treats assembly, reduction, prioritization, validation,
persistence, and lineage as six comparable gaps. They are not. Measured
against the current tree:

| Function | State | Evidence |
|---|---|---|
| **Assembly** | **Solved** | 12 generators; 8 CI drift tests assert each committed artifact byte-matches its generator's current output |
| **Validation** | **Mostly solved** | 19 checks in `verify-content-quality.py`, incl. generator drift and manifest-derived absence claims |
| **Lineage** | **Partial** | `manifest.yaml`: 115 entries with `when_to_use`. No rule → canonical-source mapping |
| **Persistence** | **Partial, ad hoc** | `planning-with-files`, `harness-feedback` (674 lines), six `.agentharness-*` state files. No lifecycle |
| **Prioritization** | **Prose only** | Precedence rules live in `CLAUDE.md` and `patterns/profiles/README.md`. Not machine-readable |
| **Reduction** | **Nothing** | No budget, no measurement, no gate. Confirmed: zero references to tokens or budgets in any tool |

Building a registry that "unifies" six functions when two are already
solved by a different mechanism risks reimplementing working machinery.
Assembly in particular is not a hand-built one-off — it is the same
generated-from-source pattern the epic proposes to introduce.

## 2. The one number that matters

Always-on context, measured 2026-07-29:

| File | Lines | ~Tokens |
|---|---:|---:|
| `CLAUDE.md` (source) | 354 | ~5,000 |
| `AGENTS.md` (generated) | 413 | ~7,830 |
| `GEMINI.md` | 419 | ~7,890 |
| `.github/copilot-instructions.md` | 418 | ~7,880 |
| `.kilo/rules/agentharness.md` | 416 | ~7,850 |

Every consuming session pays ~7,800 tokens before doing anything, plus 35
skill descriptions in the discovery index. Nothing measures this and
nothing gates it. **Reduction is the real gap**, and it is the only one
of the six with no mechanism at all.

## 3. The trap: budget enforcement without a gating strategy

The [root-instruction inventory](root-instruction-inventory-2026-07-28.md)
found that **size does not predict what is safe to remove — mechanical
enforcement does**:

| Rule | Mechanical gate | Safe to compress |
|---|---|---|
| Completion gate | `check-completion.sh` + Stop hook | ✅ |
| File placement | pre-commit hook | ✅ |
| Trunk protection | GitHub ruleset | ✅ |
| Lock protocol | pre-push + `PreToolUse` | ✅ |
| **PR-merge checklist** (~60 lines) | **none** | ❌ |
| **CI-wait rule** | **none** | ❌ |
| **Recommendation assessment** | **none** | ❌ |

`Agent Workflow Completion` is 40% of `CLAUDE.md`'s lines and 44% of its
tokens — and it is almost entirely prose-only-enforced. A context budget
that simply demanded "get under N tokens" would point straight at it.

This is not hypothetical. During the 2026-07-28/29 sessions the
prose-only merge checklist is what surfaced two real defects in
`safe-pr-merge.sh`, a mutex deadlock in `agent-lock.sh`, and a false-red
CI report — none of which had a failing test. Cutting it to hit a number
would have traded a working control for a smaller file.

**Therefore: budget measurement is safe and valuable; budget enforcement
must be paired with a gating strategy, not applied blindly.** The
cheapest way to make a section compressible is to add the hook that makes
its prose redundant.

## 4. Assessment of the Context Plane epic

**The spine idea is right.** One machine-readable registry that the
functions consume, rather than N hand-built mechanisms, is exactly the
move that worked for `manifest.yaml` → `MANIFEST.md`. Endorsed in
principle.

**The sequencing is backwards.** The epic builds Slice 0 (ADR) → 1
(registry) → 2 (budgets) → 3 (freshness) → 4 (memory) → 5 (audit CLI):
the spine first, then the views. That commits to a schema before any
consumer has demonstrated what it needs. This repo's own standing rule
says the opposite — [#143](https://github.com/andr-ca/agentharness/issues/143)
was deferred precisely because a shared contract abstracted from zero
real instances is speculation, and
[#177](https://github.com/andr-ca/agentharness/issues/177) was narrowed
to reject manifest schema fields that cannot be shown to remove a
hand-maintained duplicate.

A registry designed before two views need it will encode guesses. A
registry extracted after two views independently want the same fields
will encode facts.

**One slice should not be built:** Slice 4 (memory lifetimes) depends on
I-06, which is blocked, and its durable-knowledge half is the largest
new surface in the epic. Its task/project halves are genuinely useful,
but they are ordinary cleanup tooling that needs no registry.

## 5. Recommended build order

**Invert the epic: build the highest-value view first, standalone, and
let the spine emerge.**

### Step 1 — Measure reduction (small, no registry)

A `tools/context-budget.py` that reports always-on token cost per
generated client, and a CI gate that fails on **growth** rather than on
an absolute threshold. Growth-based gating avoids the trap in §3: it
prevents silent bloat without demanding cuts to prose that is currently
load-bearing.

Delivers the only function with zero mechanism, needs no schema, and
produces the data any later budget policy would require anyway.

### Step 2 — Make prioritization machine-readable (small)

Precedence (`explicit instruction > contract > standing rule > advisory`)
currently lives in prose in two files. Encode it once, and have the
existing `authority` CLI and `verify-content-quality.py` read it. This is
the second view.

### Step 3 — Decide the registry on evidence

With two views built, ask: do they want the same per-entry data? If yes,
extract `context.yaml` from what they already need — this is the epic's
Slice 1, but derived rather than designed. If no, they were correctly
separate mechanisms and the registry is not earned.

### Step 4 — Close lineage where it is actually broken

Not "provenance for every rule". Specifically: `CLAUDE.md`'s own
*one source of truth per rule* mandate has **no mechanical check** —
generator-vs-source drift is covered by 8 tests, but the same rule
restated differently in two prose files is not. That is the narrow, real
gap identified when [#139](https://github.com/andr-ca/agentharness/issues/139)
was renarrowed.

### Step 5 — Lifecycle tooling, if still wanted

The task/project halves of Slice 4 as plain cleanup tooling. Durable
knowledge stays blocked behind I-06's scope decision.

## 6. What completeness should mean here

"Complete context management" is worth defining before building toward
it, or the epic has no finish line:

1. Every always-on context source is **measured**, and growth is gated.
2. Every context artifact is **generated or validated** from a source of
   truth — never hand-maintained and hoped over. *(Largely true today.)*
3. Precedence between sources is **machine-readable**, not prose.
4. Every rule resolves to **one canonical location**, checkably.
5. Persistent state has a **declared lifetime** and a way to expire.

By that definition the harness is roughly 2/5 complete, and step 1 above
moves it to 3/5 for a fraction of the epic's cost.

## 7. Risks

- **Budget-driven deletion of load-bearing prose** (§3). Mitigated by
  growth-based gating and by adding hooks before cutting text.
- **Schema-first design** encoding guesses. Mitigated by the inverted
  order.
- **Reimplementing assembly**, which already works. Mitigated by scoping
  the registry to functions that lack a mechanism.
- **The epic becoming the work**: six slices plus an ADR is a
  multi-session build-out. Steps 1–2 above are each a day's work and
  deliver the measurable majority of the value.
