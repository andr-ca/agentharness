# Reviews — Operational Directory

Completed and ongoing review cycles for this repository. Files are kept flat
(rather than reorganized into subdirs on every cycle) to preserve link stability
across the INDEX.md and inter-file references.

---

## Review cycle index

### Cycle 1 — Initial repository review (2026-07-11)

| File | Purpose |
|---|---|
| [fable-review.md](fable-review.md) | Full repo review by Fable (GPT-4o) — 30 recommendations |
| [fable-review-status.md](fable-review-status.md) | Disposition of all 30 recommendations; both originally-partial items now closed |

### Cycle 2 — Independent GPT-5.6 review (2026-07-12)

| File | Purpose |
|---|---|
| [gpt-5.6-review.md](gpt-5.6-review.md) | Independent full-repository review dated 2026-07-11; baseline for the completion audit |
| [gpt-5.6-review-status.md](gpt-5.6-review-status.md) | Re-validation at `43604a7` (2026-07-12): 1 of 30 items verified complete; superseded by the follow-up below |
| [pr4-comments-status.md](pr4-comments-status.md) | Disposition of PR #4 inline review comments and later coverage/pre-push work |

### Cycle 3 — GPT-5.6 re-audit + P1/P2 batch (2026-07-13)

| File | Purpose |
|---|---|
| [gpt-5.6-completion-reaudit.md](gpt-5.6-completion-reaudit.md) | Evidence-based re-audit at `d4d2541` (2026-07-13): reclassifies 30 recommendations; repo scored 7.0/10 |
| [gpt-5.6-completion-reaudit-status.md](gpt-5.6-completion-reaudit-status.md) | Per-item response to the re-audit; scoped/low-risk items fixed inline |
| [gpt-5.6-p1-p2-followup-status.md](gpt-5.6-p1-p2-followup-status.md) | Completion status for P1-06–P1-14, confirmed-scope P2 batch, and four P2 product-direction items |
| [gpt-5.6-sol-3rdpass-2026-07-13T134419Z.md](gpt-5.6-sol-3rdpass-2026-07-13T134419Z.md) | Third-pass review |
| [gpt-5.6-sol-3rdpass-status.md](gpt-5.6-sol-3rdpass-status.md) | Disposition of third-pass findings |
| [pr9-16-comments-status.md](pr9-16-comments-status.md) | Disposition of review comments from PRs #9–16 |
| [fable-review-2026-07-13.md](fable-review-2026-07-13.md) | Follow-up Fable review dated 2026-07-13 |
| [gemini-review-2026-07-13.md](gemini-review-2026-07-13.md) | Gemini review dated 2026-07-13 |

### Cycle 4 — GPT-5.6 fourth pass + Fable disposition (2026-07-14)

| File | Purpose |
|---|---|
| [gpt-5.6-sol-4th-2026-07-14T021052Z.md](gpt-5.6-sol-4th-2026-07-14T021052Z.md) | Fourth-pass review |
| [fable-gpt5-sol-disposition-2026-07-14.md](fable-gpt5-sol-disposition-2026-07-14.md) | Cross-review disposition: Fable findings vs GPT-5.6 recommendations; source for the public-launch readiness F-xx findings |

### Cycle 5 — Harness ideation assessment (2026-07-15)

| File | Purpose |
|---|---|
| [harness-ideation-2026-07-15-status.md](harness-ideation-2026-07-15-status.md) | Disposition of an external intent-first-harness ideation note; 6 items added to ROADMAP.md (I-01…I-06) |

### Cycle 6 — Issue #240 client dogfooding (2026-08-19)

| File | Purpose |
|---|---|
| [issue-240-client-live-verification-2026-08-19.md](issue-240-client-live-verification-2026-08-19.md) | Partial — setup for live Cursor/Codex verification surfaced and fixed 3 real `generate-clients` defects (PR #243); the live-agent runs themselves remain blocked externally (Codex quota, OpenCode server error, Cursor login pending) and are not yet done |

### First dated dogfood row (2026-08-20)

| File | Purpose |
|---|---|
| [dogfood-recalium-2026-08-20-status.md](dogfood-recalium-2026-08-20-status.md) | First recorded P2-05/P2-02 dogfood row for `andr-ca/recalium` (npm mode, 2026-07-16 install). Fills the DOGFOODING.md signal table from that repo's own `harness-feedback.md` and upstream issues #76, #77, #78, #79, #88, #149, #154. Install time and context cost were never measured — recorded as "not recorded", not invented. Independent-operator half of P2-05 remains open. |

### Cycle 7 — Issue #143 recurring-loop-contract evidence pass (2026-08-23)

| File | Purpose |
|---|---|
| [issue-143-recurring-loop-contract-evidence-2026-08-23.md](issue-143-recurring-loop-contract-evidence-2026-08-23.md) | Post-hoc test of the proposed 8-field loop contract (invariant/signal/proof/authority/durable-state/retry/human-attention/retirement) against Dependabot and the scheduled link check; 6 of 8 fields generalize cleanly, durable-state and retry/escalation don't transfer for either loop; recommends re-scoping to a 6-field contract rather than building the full 8-field version |

### Cycle 8 — Issue #240 Codex live verification (2026-08-23)

| File | Purpose |
|---|---|
| [issue-240-codex-live-verification-2026-08-23.md](issue-240-codex-live-verification-2026-08-23.md) | Closes #240's Codex leg: `AGENTS.md` always-on/skill-routing confirmed live-verified working; `PreToolUse` guard confirmed live-verified **not** working — `codex_hooks` is a disabled-by-default "under development" feature flag, and even force-enabled produces zero hook-execution activity in a debug trace |

---

*For active documents not in this directory, see [../INDEX.md](../INDEX.md).*
