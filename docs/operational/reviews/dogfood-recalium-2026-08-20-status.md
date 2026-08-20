# Dogfood Row: `andr-ca/recalium`

**Dated status doc per [`docs/operational/planning/DOGFOODING.md`](../planning/DOGFOODING.md)'s
"Where findings go" — the first recorded row.**

**Timestamp:** 2026-08-20T06:20:00Z (compiled; underlying incidents span
2026-07-16 through 2026-07-23)
**Target repo:** [andr-ca/recalium](https://github.com/andr-ca/recalium)
(Python, mixed with a Tailwind/CSS frontend) — a different stack from
this repo, but **the same operator**; see "What this row does and
doesn't prove" below.
**Install:** npm mode, `--with-hook`, 2026-07-16. Harness revision
`0.2.1` at install; upgraded to `0.3.0` on 2026-07-22 via `npx
agentharness-toolkit@latest update`.
**Source:** compiled from `andr-ca/recalium`'s own
[`docs/operational/harness-feedback.md`](https://github.com/andr-ca/recalium/blob/main/docs/operational/harness-feedback.md)
(520 lines, 7 dated entries) and the 7 upstream issues it produced (#76,
#77, #78, #79, #88, #149, #154 — all closed, all fixed upstream).

## Why this doc exists

Per [ROADMAP.md](../../../ROADMAP.md)'s P2-05 entry: the friction from
this install was already filed as individual GitHub issues, which is
"not the same as the systematic comparison the plan asks for." This doc
is that systematic comparison — the [DOGFOODING.md](../planning/DOGFOODING.md)
signal table, filled in from real incidents instead of left as an
unexercised plan.

## Signal table

| Signal | What was recorded |
|---|---|
| **Install time** | Not recorded. The original `harness-feedback.md` entries capture correctness and behavior issues in detail but never a wall-clock number for `init` or `update` — a real gap in this row itself, not glossed over here. |
| **Overrides needed** | One hand-made, session-local override: after the 0.3.0 upgrade left `doctor` red (missing `pre-merge-commit` hook — see #149 below), a `.agentharness-pkg/.github/hooks/pre-merge-commit` file was hand-created to unblock `doctor` locally. Gitignored, wiped on the next `update` by design — recorded as a stopgap, not a durable fix. |
| **False positives** | None recorded. Every `doctor`/`audit` finding in the feedback log reflected a real gap (missing hook, untracked files, no lock tool) — nothing flagged that turned out to be a non-issue. |
| **Update friction** | The 0.2.1 → 0.3.0 upgrade (#149) shipped `doctor`'s *detection* of a `pre-merge-commit` hook gap without shipping the *fix* — a clean `update` landed on a doctor failure with no remediation command. Real friction, filed and fixed upstream (see disposition below). |
| **Context cost** | Not recorded — no token/size measurement was taken for the always-on router in this install. |
| **Abandoned features** | The `multi-agent-coordination` skill (#154): installed and documented as enforced, but its supporting tool (`tools/agent-lock.sh`) was never shipped into the consumer project, so the entire protocol was inert. Two sessions worked the same primary checkout concurrently with zero warning — not "unused," but *unusable as documented*, which is a sharper failure than a feature nobody tried. |
| **Net verdict** | **Would keep.** Every one of the 7 issues this install surfaced was a real, structural gap — not a misunderstanding or a one-off operator slip — and every one was fixed upstream (see below). The harness caught real mistakes in the reporting repo too: a trunk-protection hook gap on `git merge --no-ff` (#76) and a "merged 3 PRs on green CI alone, twice, including on the PR about the first miss" incident (#77) that the router's own installed mandate should have prevented and, once tightened, now would. |

## The 7 issues, and what each closed

| Issue | Finding | Resolution |
|---|---|---|
| [#76](https://github.com/andr-ca/agentharness/issues/76) | Trunk-protection hook doesn't fire on `git merge --no-ff` onto `main` — only `pre-commit` was covered, not the merge-commit path | Closed. `pre-merge-commit` hook shipped, delegating to the same `prevent-trunk-commit` script. |
| [#77](https://github.com/andr-ca/agentharness/issues/77) | "Give automated review time to post" had no concrete threshold — the mistake repeated on the very next PR, including the PR documenting the first miss | Closed. The router mandate now specifies a concrete poll loop and a reviewer-configured check — this session's own PR merges (#248, #250, #251) used exactly that protocol via `tools/safe-pr-merge.sh`, built in direct response to this finding. |
| [#78](https://github.com/andr-ca/agentharness/issues/78) | No mechanism surfaced a pre-existing PR sitting 5 days with unaddressed, security-relevant review comments | Closed. `CLAUDE.md` now instructs checking `gh pr list --state open` for stale unaddressed comments at the start of any session, not only on PRs being actively merged. |
| [#79](https://github.com/andr-ca/agentharness/issues/79) | Feature request: an enforced (not just advisory) monitor→log→file loop for harness friction itself | Closed. The harness-feedback skill and its standing "don't wait to be asked" mandate exist because of this request. |
| [#88](https://github.com/andr-ca/agentharness/issues/88) | npm-mode install left 30+ files untracked with no signal — later found broader (every file `init` writes in npm mode, not just skills) | Closed. Fixed upstream; also self-corrected in two follow-up comments once the reporter verified the original claim was narrower than first stated (the "32 files" were symlinks, not independent content) — the corrections were posted rather than left standing. |
| [#149](https://github.com/andr-ca/agentharness/issues/149) | 0.3.0 shipped `doctor`'s detection of a missing `pre-merge-commit` hook without shipping the hook itself, so a clean `update` landed on red | Closed. |
| [#154](https://github.com/andr-ca/agentharness/issues/154) | `multi-agent-coordination`'s lock tool was never installed into consumer projects, making the documented protocol entirely inert; two sessions collided undetected on the same checkout | Closed via #159. |

## What this row does and doesn't prove

**Proves:** real, structural gaps exist that no fixture (`examples/*-project/`)
could have found — every one of these 7 issues required a real
multi-week install under real, non-scripted use to surface. The harness
was also responsive: every issue was fixed, most within a day or two of
filing.

**Doesn't prove:** generalization beyond one operator. Per
[ROADMAP.md](../../../ROADMAP.md)'s P2-05 entry, both current dogfood
targets (`recalium` and `infoocode`) belong to the same operator as this
repo — correlated blind spots, the explicit reason fixtures alone
aren't trusted here, remain untested. A repo with a different user
entirely is still the open half of P2-05/P2-02, not closed by this row.
