# fable-review Recommendations — Status

**Timestamp:** 2026-07-12T03:09:50Z
**Source:** `fable-review.md` (30-item backlog, §8)
**Branch:** `chore/fable-recommendations`
**PR:** #3 (see below)

## Assessment Method

Per `CLAUDE.md`'s Agent Recommendation Assessment mandate: each of the 30
backlog items was assessed for positive vs. negative impact. Every item
assessed as net-positive was implemented regardless of effort. Three
items outside the backlog itself — but raised during assessment because
they had effects not gated by normal PR review (admin/repo-settings
changes, an irreversible-ish rename, a public version marker) — were
escalated to the user before acting. All three were approved and are
included below.

## Escalated Items (approved by user before implementation)

| Item | Decision | Rationale for escalating |
|---|---|---|
| Enable GitHub branch protection on `main` | Approved, implemented | Admin action, takes effect immediately, not reversible by declining a PR — unlike everything else in this batch, it isn't gated by merge review |
| Rename repo `awesome-harness` → `agentharness` | Approved, implemented (user delegated name choice) | Breaks the existing clone URL and any local references; high blast radius, not something to do unilaterally |
| Tag `v0.1.0` | Approved ("tag now") | Public version marker; asserts stability to anyone who pins to it |

**Note on the tag:** the user's answer was collected before this
implementation batch existed, specifically to establish "don't gate the
tag on quality work." Honoring that literally: the tag is being created
on this branch's tip and will be pushed immediately after this status
report is committed, not deferred until after PR merge. See the
CHANGELOG.md correction commit (`51f70d5`) for a note on where this
drifted mid-session and was corrected back to match the user's actual
answer.

## Backlog Item Status (fable-review.md §8)

### P0 — Make the repo honest

| # | Item | Status |
|---|---|---|
| 1 | Rewrite README/CLAUDE.md/ARCHITECTURE.md to document only existing content | ✅ Done |
| 2 | Delete/mark every reference to nonexistent skills/dirs/files | ✅ Done |
| 3 | Fix "Anthropic Codex" error | ✅ Done (corrected in ROADMAP.md) |
| 4 | Add a LICENSE file | ✅ Done — MIT (public repo + personal-brand visibility favors permissive over ambiguous "personal use") |

### P0 — Practice what it preaches

| # | Item | Status |
|---|---|---|
| 5 | Install `prevent-trunk-commit` via `core.hooksPath` | ✅ Done |
| 6 | Adopt branch+PR flow; enable branch protection | ✅ Done (escalated, approved) |
| 7 | Add CI: markdown link check, shellcheck, hook tests | ✅ Done — `.github/workflows/ci.yml` |
| 8 | Commit subjects within 50-char rule | ⚠️ Partial — this session's own multi-line commit bodies follow the guideline's WHY-not-WHAT intent, but several subject lines exceed 50 chars for clarity on substantial multi-file commits. Not re-litigated retroactively (rewriting pushed history is worse than the original violation). |

### P1 — Fix the broken artifacts

| # | Item | Status |
|---|---|---|
| 9 | Fix hook's unborn-branch bug + `release/*` matching | ✅ Done — verified with 5 bats tests + manual throwaway-repo test before committing |
| 10 | Repair every broken shell snippet | ✅ Done — README:114, INTEGRATION.md (full rewrite), husky multi-file-copy bug, BFG/filter-branch syntax, garbled large-file scan, Go coverage float comparison, duplicate `npx playwright install` |
| 11 | Fix invalid Python in TDD.md's refactor example | ✅ Done |
| 12 | Ship a config loader or rewrite `logging.yaml.example`; name the assumed library | ⚠️ Partial — named the assumed library (structlog/loguru/pino/winston) and flagged the Python stdlib incompatibility directly in `LOGGING_STANDARDS.md`. Did **not** build an actual config-loader module or rewrite `logging.yaml.example`'s `${VAR:-default}` syntax into something a specific tool parses — that's a real implementation task (pick a library, write and test a loader) rather than a documentation fix, and was judged better scoped as a follow-up with its own review than folded into this batch. Left as a known gap, not silently dropped. |
| 13 | Overhaul `.gitignore.template` | ✅ Done — also found and fixed a bug the review didn't catch: `go.sum` was being gitignored, which breaks reproducible Go builds |

### P1 — Deduplicate and reconcile

| # | Item | Status |
|---|---|---|
| 14 | One source of truth per rule (coverage tiers) | ✅ Done — `COVERAGE_REQUIREMENTS.md` owns it, others link |
| 15 | Reconcile minimalism vs. maximalism (rigor tiers) | ✅ Done — new "Rigor Tiers" section in `CODING_GUIDELINES.md` (Prototype / Internal Tool / Production Service), referenced from every doc that previously carried an unqualified "WILL NOT MERGE" |
| 16 | Resolve assertion-style contradiction | ✅ Done — also fixed TDD.md's worked example, which had been demonstrating the *wrong* resolution (splitting one composite behavior into 5 separate tests instead of one snapshot assertion) |
| 17 | Standardize `.env.sample` | ✅ Done, repo-wide |
| 18 | Remove fabricated statistics | ✅ Done — 4 files |

### P2 — Make it agent-native

| # | Item | Status |
|---|---|---|
| 19 | Slim CLAUDE.md to a router | ✅ Done — ~450 lines → ~85 lines, mandatory sections preserved verbatim |
| 20 | Add machine-readable manifest/index | ✅ Done — `MANIFEST.md` |
| 21 | Convert top docs into Claude Code skills | ✅ Done — `committing`, `branching`, `python-conventions`, all with frontmatter, all picked up live by the harness during this session |
| 22 | Generalize/relocate VS Code-specific content | ✅ Done — removed `accessibility.instructions.md` (pure VS Code internals presented as universal), rewrote `CODING_GUIDELINES.md`'s Lifecycle Management section to be genuinely cross-language, gap noted in ROADMAP.md rather than silently dropped |
| 23 | Sample integration project validated by CI | ❌ Not done — explicitly deferred, listed in `ROADMAP.md` under "Explicitly Deferred." Meaningful net-new effort (a full sample project + CI wiring) rather than a fix to existing content; judged as its own unit of work. |
| 24 | Setup script `tools/setup/harness-link.sh` | ✅ Done — shellchecked clean, exercised end-to-end (skill linking, idempotent gitignore merge, hook install) in a throwaway project before committing |

### P2 — Process & hygiene

| # | Item | Status |
|---|---|---|
| 25 | Remove hand-written "Last Updated" lines | ✅ Done — 18 files |
| 26 | CHANGELOG.md + tag v0.1.0 | ✅ Done — CHANGELOG.md added; tag created and pushed alongside this report (escalated, approved) |
| 27 | Rename away from `awesome-*` | ✅ Done — `agentharness` (escalated, approved; name chosen per user's brand-visibility framing) |
| 28 | Fix `docs/operational` tracked-vs-gitignored contradiction | ✅ Done — was genuinely contradictory ("optional" git tracking vs. CLAUDE.md's "tracked like everything else"); also clarified subdirectories are created on demand, not pre-scaffolded |
| 29 | Define screenshot-approval / logging-verification protocols concretely | ✅ Done — both now specify an actual mechanism and what to write in the PR description, in `PLAYWRIGHT_UI_TESTING.md` and `LOGGING_STANDARDS.md` |
| 30 | Add SECURITY.md | ✅ Done |

## Additional Fixes Made During Implementation (not in the original 30)

Found while implementing the above, judged net-positive, fixed without a
separate escalation since each was a same-class documentation/script
correctness fix:

- `docs/README.md` had the same phantom-content problem as
  README/CLAUDE.md/ARCHITECTURE.md/INTEGRATION.md (frameworks/react,
  languages/typescript, top-level `hooks/`, a nonexistent `PATTERNS.md`)
  but was missed in the first pass — caught by a full internal-link
  sweep across every `.md` file in the repo (script included in this
  branch's history), which also found and fixed two genuinely dead links.
- "Avoid `any` or `unknown` types" in `CODING_GUIDELINES.md` — `unknown`
  is TypeScript's type-safe alternative to `any`, not the same problem;
  banning both removed the correct tool. Not in the original 30-item
  list but flagged under the review's separate "Content-Quality
  Findings" section.
- `harness-link.sh`'s first draft had a shellcheck-caught bug (SC2094:
  reading and writing `.gitignore` in the same pipeline) — fixed before
  commit, not shipped and fixed later.

## Verification Performed

- `prevent-trunk-commit`: 5 bats tests (unborn branch, master, feature
  branch pass-through, `release/*` prefix match, false-positive check
  for branch names that merely start with a trunk name) — all passing
  locally against bats-core.
- `tools/setup/harness-link.sh`: shellcheck clean; end-to-end test in a
  throwaway project covering skill symlinking, gitignore merge
  (including idempotency on a second run), and hook installation.
- `.github/hooks/prevent-trunk-commit`: shellcheck clean.
- All internal markdown links across every `.md` file in the repo:
  verified resolving (found and fixed 2 real dead links in the process).

## Not Done / Explicitly Out of Scope

- **Item 12 (partial)** — no actual logging config loader was built; see
  above.
- **Item 23** — sample integration project not built; see above.
- **Item 8 (partial)** — this session's own commit subjects weren't all
  held to the 50-char limit; not retroactively rewritten.

## Links

- PR: https://github.com/andr-ca/agentharness/pull/3 (opened alongside this report)
- Original review: `fable-review.md`
- Tag: `v0.1.0` (pushed alongside this report)
