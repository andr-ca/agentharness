---
date: 2026-08-05
status: draft
topic: context-plane
purpose: Scope gate for the Context Plane epic (#194) — ownership boundary, registry schema, and how it subsumes ROADMAP P2-04 and I-06 instead of leaving three overlapping entries.
related-harness: manifest.yaml, tools/generate-manifest.py, tools/verify-content-quality.py (check_manifest_md_sync), ROADMAP.md
---

# Context Plane Slice 0: scope ADR + design doc

## Status

Draft. This is the scope gate for issue #194 (Context Plane epic) —
per the Recommendation Assessment mandate, slices 1–5 don't start until
this is approved. Scope decided 2026-08-05: **build slices 0, 1, and 3
only.** Slices 2 (budgeting), 4 (lifecycle tooling), and 5 (audit CLI)
are deferred pending measured evidence they solve a real problem — see
"Deferred scope" below.

## Problem

Issue #193's audit scored this repo's context-management coverage and
found two real, named gaps that already had unbuilt ROADMAP entries
pointing at each other without ever meeting:

- **P2-04** ("policy provenance model"): owner/source, rationale,
  applicability, enforcement mechanism, last-review date per rule, as
  structured data — the semantic sibling of the already-shipped
  `manifest.yaml` (assembly index).
- **I-06** ("repository context contract"): committed, provenance-tagged
  repository context with a freshness marker and staleness-invalidation
  rules. Previously blocked on the PR #47 scope decision — **that PR
  merged 2026-07-16** (confirmed via `gh pr view 47`), so the blocker no
  longer applies.

Both describe the same missing thing from different angles: a single
registry that knows what context exists, who's allowed to say so, and
whether it's still fresh. Building them separately would duplicate the
manifest pattern a second time instead of extending it.

## Ownership boundary (closes #193 item 6)

**The harness owns governed, versioned, deterministic context.** That
means: what loads (`manifest.yaml`'s assembly index), in what authority
order (`CLAUDE.md`'s precedence rules), under what budget class, with
what provenance, and whether it's still fresh enough to trust.

**Runtime context is explicitly out of scope.** Summarization, RAG-style
retrieval, learned cross-session memory, and token-budget-driven context
compression are the *consuming agent's* runtime behavior, not something
a policy/governance harness assembles or owns. This repo ships policy
and portable patterns; it does not ship an agent runtime. As a follow-up
(not part of this PR), `docs/ARCHITECTURE.md` should get one line
pointing here so a future audit doesn't re-raise long-term memory as a
silent gap (#193 item 6's ask).

This boundary is also why Slice 4 (memory lifetime tooling) is deferred,
not built as scoped: automated expiry/promotion of *memory* is runtime
behavior, whereas a freshness marker on *registered context* (Slice 3)
is squarely governance.

## Registry schema (Slice 1 — `context.yaml`)

One entry per registered context asset, following `manifest.yaml`'s
existing generated-from-source convention (source of truth is
`context.yaml`; a generated view is validated for drift the same way
`check_manifest_md_sync()` already validates `MANIFEST.md`):

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable key, unique across the registry |
| `path` | string | Repo-relative path to the asset |
| `kind` | enum | `policy` \| `pattern` \| `generated` \| `repository-fact` |
| `authority` | enum | Tier in `CLAUDE.md`'s existing precedence order (explicit-instruction > authority-contract > publish-mode flag > default), so provenance ties back to a rule that already exists rather than inventing a second hierarchy |
| `lifecycle` | enum | `task` \| `project` \| `durable` — see below |
| `loading` | enum | `always-on` \| `on-demand` (mirrors skills' progressive-disclosure model, and the terminology `docs/CLIENT_COMPATIBILITY.md` already uses) |
| `provenance` | enum | `verified` \| `inferred` \| `declared` \| `unknown` — the vocabulary I-06 already named as independently adoptable |
| `freshness` | object | `{ last_reviewed: date, staleness_rule: string }` — Slice 3 validates against this |

`budget_class` is deliberately **not** in the Slice-1 schema. Budgeting
was Slice 2, and it's deferred (see below); adding the field now without
a consumer would be exactly the kind of speculative field this repo's
own "no code for hypothetical future requirements" rule warns against.
If Slice 2 is ever scoped in, it's an additive column, not a migration.

Three `lifecycle` values, distinguishing this from a flat manifest:

- **task** — scoped to one working session; not meant to survive a
  context reset (e.g. a `planning-with-files` scratch file).
- **project** — durable for the life of a repo/branch but not portable
  across projects (e.g. `docs/operational/*` review notes).
- **durable** — portable, versioned policy content this harness itself
  ships (e.g. `CLAUDE.md`, `patterns/*`).

## Mapping table — what this subsumes

| ROADMAP/issue entry | Disposition |
|---|---|
| P2-04 (policy provenance model) | Superseded by this registry's `authority`/`provenance`/`freshness` fields — ROADMAP.md's P2-04 line gets replaced with a pointer to this doc instead of carrying a second unbuilt description of the same thing |
| I-06 (repository context contract) | Unblocked (PR #47 merged) and superseded — the provenance vocabulary I-06 called "independently adoptable" is Slice 1's `provenance` field; the "freshness marker and staleness-invalidation" half is Slice 3 |
| #193 item 1 (provenance vocabulary) | Closed by Slice 1 |
| #193 item 2 (forgetting/expiry policy for `docs/operational/`) | Deferred with Slice 4 — see below |
| #193 item 3 (drift-checking beyond `MANIFEST.md`) | Closed by Slice 3, generalizing `check_manifest_md_sync()`'s pattern to registry entries |
| #139, #177 | Addressed — the registry is the machine-readable context/task-route foundation both were asking for |
| #175 | Addressed — this ADR's ownership-boundary section is the constitution/procedure split #175 wanted written down |

## Deferred scope, and why

- **Slice 2 (budgeting):** no measured evidence yet that context volume
  is actually causing overload for this harness's consumers. Skills stay
  on-demand by default (already true today). Revisit if real friction
  shows up.
- **Slice 4 (lifecycle tooling — promote/expire automation):**
  `docs/operational/README.md` already has a working manual
  promote/archive/delete workflow. Automating it is additive machinery
  for a problem that isn't measured yet. Also crosses the ownership
  boundary above if it starts touching runtime memory rather than
  registered context.
- **Slice 5 (`context audit` CLI):** a stale registry entry is already
  visible via CI (the same mechanism that already catches `MANIFEST.md`
  drift). A dedicated audit command adds a new surface without a
  demonstrated gap the existing gate doesn't cover.

If any of these prove necessary later, they're additive layers on a
registry that already exists — not blocked by deferring them now.

## Next steps

Slice 1 (`context.yaml` schema + populate) and Slice 3 (freshness
validation gate) are scoped in per the table above. Implementation
starts in separate PRs once this doc is merged.
