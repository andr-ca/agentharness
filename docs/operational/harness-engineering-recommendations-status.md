---
date: 2026-07-22
status: completed
topic: reviews
purpose: Disposition of roadmap ideas assessed from harness-engineering
related-harness: ROADMAP.md
---

# Harness-engineering recommendations status

**Timestamp:** 2026-07-22T10:41:27Z

**Reference checkout:** `lopopolo/harness-engineering` at
`226c8d35fb6ea3ed55467753dba6dea2b5fd5778`

**Agreed scope:** Assess ideas for agentharness; do not replicate the source
architecture. Treat existing roadmap directions as MVPs and assess whether
expanding product boundaries is justified.

**Implementation status:** Recommendations filed only; no feature
implementation was authorized or performed.

**Lifecycle:** Retain while issues #137–#143 are open. Archive after they are
closed or their accepted scope is incorporated into `ROADMAP.md`.

## Outcome

Seven consolidated feature recommendations were filed. The strongest source
ideas generally fit as evolutions of current agentharness assets. Runtime-heavy
variants were either bounded behind evidence gates or kept as explicit
non-goals.

| Issue | MVP/current baseline | Change | Improvement |
|---|---|---:|---:|
| [#137 — Claim-matched proof contracts](https://github.com/andr-ca/agentharness/issues/137) | ROADMAP I-01, completion gate, PR verification, live-verification rule | Medium | High |
| [#138 — Whole-journey harness reviews](https://github.com/andr-ca/agentharness/issues/138) | ROADMAP P2-01/P2-02/P2-03 and deterministic eval scaffold | High | Massive |
| [#139 — Provenance, repository context, then context selection](https://github.com/andr-ca/agentharness/issues/139) | ROADMAP P2-04 followed by I-06 | Medium → High; curator service would be Massive | High for contracts; curator unproven |
| [#140 — Scoped authority contracts](https://github.com/andr-ca/agentharness/issues/140) | Implemented P0-03 publish authority and local safety controls | High | High |
| [#141 — Privacy-safe evidence learning loop](https://github.com/andr-ca/agentharness/issues/141) | Implemented #79 feedback skill, P2-02, and P2-07 | Medium | Medium–High |
| [#142 — Dependency ownership](https://github.com/andr-ca/agentharness/issues/142) | Existing dependency-audit skill and pinned dependencies | Low | Medium |
| [#143 — Recurring maintenance-loop contracts](https://github.com/andr-ca/agentharness/issues/143) | Agentic-loop guidance and concrete recurring workflows | Medium | Medium |

## Per-recommendation rationale

### #137 — Claim-matched proof contracts

**Positive:** Closes the gap between a passed check and evidence for the exact
claim being made. It composes with completion, audit-followup, and eval work.

**Negative/risk:** A universal attestation system would add schema and storage
cost without proportional value. The issue therefore recommends a compact
contract and optional structured metadata, using I-01 as the first MVP.

**Installer benefit:** Reviewers can identify what was actually verified,
against which artifact, and what remains uncertain.

### #138 — Whole-journey harness reviews

**Positive:** Tests the product's actual promise—better accepted outcomes with
less corrective human work—rather than only file correctness.

**Negative/risk:** Live evaluations cost money and can become noisy model
benchmarks. The issue keeps the runner pluggable, pins conditions, requires
repeats, and treats P2-01/P2-02/P2-03 as the MVP rather than adding a parallel
review subsystem.

**Installer benefit:** Users get evidence that the harness helps realistic
workflows and can see regressions that fixtures miss.

### #139 — Provenance, repository context, then context selection

**Positive:** P2-04 and I-06 provide a coherent path from semantic policy
ownership to trustworthy repository context. A later local selector could
reduce context overload.

**Negative/risk:** A resident curator, remote semantic index, or autonomous
rewriter would create a new runtime/data product before the simpler context
contract is proven. Those variants require a separate future decision.

**Installer benefit:** Users can trace rules to canonical sources and give
agents compact, freshness-aware context without silently adopting a service.

### #140 — Scoped authority contracts

**Positive:** Extends the safe binary publish default into least-authority
grants for real operations, targets, and lifetimes.

**Negative/risk:** Cross-client enforcement capabilities differ, and a false
claim of enforcement is worse than explicit advisory policy. Credential
storage and remote authorization are excluded.

**Installer benefit:** Users can authorize only the operation a task needs and
see the effective scope before and after work.

### #141 — Privacy-safe evidence learning loop

**Positive:** Makes the implemented feedback loop easier to aggregate and
corroborate across versions and consumers.

**Negative/risk:** Raw transcript ingestion creates privacy, retention, trust,
and noise problems. The recommendation stays local and opt-in, and requires
evidence before feedback becomes policy.

**Installer benefit:** Recurring friction becomes actionable without uploading
proprietary prompts, code, or conversations.

### #142 — Dependency ownership

**Positive:** Adds trust, capability exposure, provenance, maintenance, and
replacement burden to an already useful vulnerability/lockfile audit.

**Negative/risk:** Applying the same ceremony to every development tool would
create friction. Risk tiers and optional automation keep the change
proportionate.

**Installer benefit:** Users understand both the immediate and ongoing risk of
dependencies, agent plugins, and third-party actions.

### #143 — Recurring maintenance-loop contracts

**Positive:** Extracts reusable safety and evidence rules from existing
scheduled/update workflows without prescribing an execution platform.

**Negative/risk:** A generic pattern may be premature or invite an
orchestration subsystem. The issue requires two concrete dogfood cases before
promotion and excludes schedulers, daemons, and automatic merge services.

**Installer benefit:** Recurring maintenance becomes bounded, retryable, and
clear about when human intervention is required.

## Folded or bounded ideas

- **Standalone repository-review subsystem:** not a separate roadmap item.
  Its useful whole-job trajectory concepts are future stages of #138 and the
  existing P2 eval/dogfood work.
- **Context-curator service:** not committed. P2-04 and I-06 are the MVPs;
  stateless local context selection is a measured future option in #139.
- **Raw session-log learning:** rejected. Structured local, corroborated
  feedback is recommended in #141; raw/default telemetry remains outside the
  product boundary.
- **Credential/authority service:** rejected. Declarative scoped authority is
  recommended in #140; credential brokerage and remote authorization remain
  outside the product boundary.
- **General tool-capability catalog:** no separate issue. Current manifest,
  audit JSON, client-compatibility documentation, and #110 cover the observed
  need; new schema should follow a demonstrated recovery/discovery failure.
- **General orchestration runtime:** no separate issue. Proof, eval, and
  scheduler-neutral loop contracts capture the useful policy while preserving
  agentharness's portable-product boundary.

## Recommended sequencing

1. Low-cost dependency-ownership extension (#142).
2. I-01 proof contract and P2-04 policy provenance (#137, first stage of #139).
3. Live outcome/instruction evals and real dogfood (#138).
4. Scoped authority and structured feedback, informed by eval evidence
   (#140–#141).
5. Repository context and maintenance-loop incubation (#139, #143).
6. Reconsider curator-like or stronger runtime capabilities only after the
   preceding stages demonstrate a concrete unmet need.

## Publication record

The issues were created through the authenticated GitHub CLI with the
`enhancement` label. No pull request implements them; each remains a roadmap
recommendation requiring its own scoping decision under the repository's
recommendation-assessment policy.
