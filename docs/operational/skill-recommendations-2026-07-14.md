# Optional Skill Recommendations — 2026-07-14

**Status:** Analysis & recommendations (not implementation)
**Author:** Agent (GitHub Copilot / Claude Sonnet 4.6)
**Scope:** Identify up to 15 optional skills worth adding to the harness

---

## Background

The harness currently ships 7 skills:

| Skill | Category |
|---|---|
| `agentic-loops` | Agent workflow |
| `audit-review-followup` | Review process |
| `branching` | Git workflow |
| `committing` | Git workflow |
| `error-handling` | Code patterns |
| `port-agent-config` | Tooling migration |
| `python-conventions` | Language conventions |

The set covers the core agent-safety loop (branching, committing, review, loop
mechanics) and one language (Python). It is thin on: language breadth, code
quality patterns, and task-management workflows.

## Research Sources

1. **awesomeskill.ai** — The leading marketplace for open-source agent skills.
   Homepage content was fetched on 2026-07-14. The site is a JavaScript SPA;
   full catalogue browsing requires a live browser session. The subset visible
   in the initial HTML render is documented below.
   URL: https://awesomeskill.ai/

2. **Harness's own content** — Several skill topics already have supporting
   material in `patterns/`, `languages/`, and `frameworks/` that is not yet
   wrapped as a skill and surfaced via the on-demand mechanism.

3. **ROADMAP.md** — The planned component list, specifically `patterns/api-design`
   and the language/framework gaps flagged there.

### awesomeskill.ai — Skills Visible in Initial Render

| Skill name | Description (truncated) | Downloads |
|---|---|---|
| `agent-browser` | Browser automation CLI for AI agents | 28,079 |
| `web-design-guidelines` | Review UI code for Web Interface Guidelines compliance | 24,686 |
| `find-skills` | Helps users discover and install agent skills | 13,308 |
| `ui-ux-pro-max` | UI/UX design intelligence — 50 styles, 21 palettes, 9 stacks | 13,550 |
| `content-research-writer` | Writing + research with citations | 17,665 |
| `planning-with-files` | Manus-style file-based planning (task_plan.md, findings.md, progress.md) | 8,675 |
| `react-best-practices` | React and Next.js optimization from Vercel Engineering | 2,306 |
| `seo-review` | Focused SEO audit on JavaScript concept pages | 66,092 |
| `using-superpowers` | Establishes skill-first workflow at conversation start | 20,861 |
| `notebooklm` | Query Google NotebookLM notebooks from Claude Code | 1,724 |
| `enterprise-sales` | Navigate enterprise sales, closing large deals | 1,135 |
| `semanticscholar-skill` | Search academic papers via Semantic Scholar API | (listed) |

Note: The full catalogue contains many more skills; the above is the visible
subset from the homepage render. `seo-review`'s 66K downloads makes it the
most-downloaded skill on the platform — likely reflecting strong organic
search traffic, not necessarily deep developer-audience demand.

---

## Recommended Skills

### Tier 1 — Fill harness content gaps (wrap existing material)

These are the highest-priority additions because the harness already contains
the substance; the only work is writing a `SKILL.md` wrapper and adding it to
the registry.

---

#### 1. `typescript-conventions`

**Description trigger:** Use when writing, reviewing, or refactoring TypeScript
or JavaScript code — naming conventions, type annotations, common pitfalls
(any-escape, non-null assertions, implicit any from missing tsconfig), and
module structure.

**Rationale:** `python-conventions` is the harness's most reachable
language-specific skill. TypeScript is the second language with a full
`CONVENTIONS.md` at `languages/typescript/CONVENTIONS.md` and a framework
layer at `frameworks/react/CONVENTIONS.md`. Wrapping this as a skill makes it
discoverable by Claude Code, Codex, and Cursor the same way `python-conventions`
is. Many consumer projects are TypeScript-first; the gap between the Python
skill's availability and the absence of an equivalent TypeScript skill is
obvious and easy to close.

**Source material:** `languages/typescript/CONVENTIONS.md`,
`frameworks/react/CONVENTIONS.md`

**Effort to build:** Low — same shape as `python-conventions`, content exists.

---

#### 2. `go-conventions`

**Description trigger:** Use when writing, reviewing, or refactoring Go code —
naming conventions, error wrapping idioms, interface design, goroutine safety,
and common pitfalls (goroutine leaks, misuse of defer in loops, nil map writes).

**Rationale:** Go is the third supported language with a full `CONVENTIONS.md`
at `languages/go/CONVENTIONS.md`. The same argument applies as TypeScript:
content exists, a skill wrapper would unlock on-demand triggering. Go is
heavily used in infrastructure, DevOps, and CLI tooling — the harness's
primary adopter profile. This is arguably more impactful than the TypeScript
addition for that audience.

**Source material:** `languages/go/CONVENTIONS.md`

**Effort to build:** Low — same shape as `python-conventions`.

---

#### 3. `testing`

**Description trigger:** Use when writing tests, deciding on test coverage,
choosing between unit/integration/E2E tests, applying TDD, or reviewing test
quality — covers rigor tiers, TDD workflow, coverage requirements, and
Playwright for UI testing.

**Rationale:** The harness has extensive testing content: `patterns/testing/`
contains `TDD.md`, `COVERAGE_REQUIREMENTS.md`, `PLAYWRIGHT_UI_TESTING.md`,
`COMPLETION_CHECKLIST.md`, and `README.md`. This is the harness's own
dogfooded standard. Making it discoverable as a skill would let consuming
projects invoke it explicitly when writing tests, rather than relying on the
agent to infer it from the CODING_GUIDELINES. This is especially valuable
for teams adopting the harness's rigor-tier system.

**Source material:** `patterns/testing/`

**Effort to build:** Medium — content is rich but needs distilling into a
skill summary vs. referencing multiple files.

---

#### 4. `logging`

**Description trigger:** Use when adding logging to an application, reviewing
log output, choosing log levels, structuring logs for observability, or loading
logging configuration — covers structured logging, YAML config patterns, local
vs. production output.

**Rationale:** `patterns/logging/` contains `LOGGING_STANDARDS.md`,
`logging.yaml.example`, `config_loader.py`, and its tests. The standards are
already written and tested. A skill wrapper would make this accessible on
demand — particularly useful for backend services and data pipelines that need
consistent log structure.

**Source material:** `patterns/logging/LOGGING_STANDARDS.md`,
`patterns/logging/logging.yaml.example`

**Effort to build:** Low.

---

#### 5. `accessibility`

**Description trigger:** Use when building or reviewing web UIs for
accessibility — WCAG 2.2 compliance, ARIA patterns, keyboard navigation,
color contrast, screen reader compatibility, and accessible component design.

**Rationale:** `patterns/accessibility/README.md` exists (added in a recent
P-session). This is a cross-language, cross-framework concern with clear
regulatory relevance (EU EAA 2025, ADA, WCAG 2.2). The `web-design-guidelines`
skill on awesomeskill.ai has 24,686 downloads, which signals strong demand for
an agent skill in this space. The harness already has the authoritative content;
wrapping it as a skill makes it comparable to the market offering.

**Source material:** `patterns/accessibility/README.md`

**Effort to build:** Low.

---

### Tier 2 — High-value new skills (no existing content)

These require writing original skill content but address clear, high-frequency
developer workflows that the harness is silent on today.

---

#### 6. `security-review`

**Description trigger:** Use when reviewing code for security vulnerabilities,
performing a security audit, or checking for common OWASP Top 10 issues —
covers injection flaws, broken authentication, sensitive data exposure,
insecure deserialization, and dependency vulnerability checks.

**Rationale:** Security is the highest-stakes gap in the harness's current
skill set. The harness's own `copilot-instructions.md` already says: "Ensure
your code is free from security vulnerabilities outlined in the OWASP Top 10."
But there is no skill the agent can load to *apply* that standard
systematically. A `security-review` skill would close the gap between the
stated mandate and the actionable guidance. This is a P0 safety concern for
any project that ships to production, and it aligns with the harness's stated
goal of making "what's written once referenced everywhere."

**Proposed content:** OWASP Top 10 checklist for code review; language-specific
vulnerability patterns (Python: eval/pickle/SQL f-strings; TypeScript:
prototype pollution, XSS via dangerouslySetInnerHTML; Go: SSRF from unchecked
URLs); guidance on `gh secret scan` and `trufflesecurity/trufflehog` for
secrets; dependency audit commands (`pip-audit`, `npm audit`, `govulncheck`).

**Effort to build:** Medium — requires careful, accurate content; can be
scoped to OWASP Top 10 + language quick-reference for v1.

---

#### 7. `planning-with-files`

**Description trigger:** Use when starting a complex multi-step task, a
research project, or any task that requires more than 5 tool calls — creates
and maintains `task_plan.md`, `findings.md`, and `progress.md` to preserve
state across context resets.

**Rationale:** This is the third-most-downloaded skill in the awesomeskill.ai
visible set (8,675 downloads). The "planning-with-files" pattern (Manus-style:
write a plan file, write findings as you go, update progress) solves a real
pain point: long-running agent tasks that lose context mid-way. The harness
has `docs/operational/` as a working-docs convention but no skill-level
guidance on how an *agent* should manage its own task state. Adopting or
adapting this pattern as a skill would make the harness usable for long,
multi-turn coding tasks (migrations, refactors, new feature buildouts).

**Note on sourcing:** awesomeskill.ai's version is open-source; the harness
could adapt its pattern under its own conventions rather than importing it
verbatim — the key content (when to create the files, their structure, how
to update them atomically) is short and well-understood.

**Effort to build:** Low-medium — short skill, well-scoped pattern.

---

#### 8. `requirements-clarification`

**Description trigger:** Use before implementing a significant feature or
change when requirements are ambiguous, underspecified, or likely to have
multiple reasonable interpretations — covers structured discovery, one
question at a time, edge-case probing, and writing a brief requirements
summary before coding starts.

**Rationale:** A large share of agent-generated code is wasted because the
agent optimistically starts implementing before the scope is clear. The harness
currently runs agents in "ask-user" mode (the current VS Code mode) which
enforces a plan-before-implement loop, but there is no skill-level guidance
on *how* to do requirements discovery well. A skill here would be referenced
by any skill that involves building something new, and would directly reduce
the review cycle length. This is a high-leverage meta-skill.

**Effort to build:** Medium — content is well-established (structured
discovery, ambiguity checks, INVEST criteria for user stories) but needs
adapting to the agent-workflow context rather than a waterfall-PM context.

---

#### 9. `code-review`

**Description trigger:** Use when reviewing a diff, pull request, or code
change — systematic checklist for correctness, clarity, security, testability,
and adherence to the project's conventions.

**Rationale:** The harness has a strong `audit-review-followup` skill for
*following up* on reviews that were already done, but no skill for *conducting*
a code review in the first place. Agent-conducted code review is a high-demand
workflow (GitHub Copilot Code Review, Claude Code's review mode, etc.). A
skill that formalizes the checklist — correctness, edge cases, test coverage,
naming, security, performance hot spots — would make the harness's reviewing
posture explicit and consistent across all tooling.

**Effort to build:** Medium.

---

#### 10. `api-design`

**Description trigger:** Use when designing, reviewing, or evolving a REST or
GraphQL API — resource naming, HTTP status codes, versioning strategy, error
response shapes, pagination, and rate limiting.

**Rationale:** The ROADMAP explicitly calls out `patterns/api-design` as
planned-but-not-built. API design is the most common surface for cross-team
consistency failures in larger projects. A skill here would complement the
existing `error-handling` skill (which already covers downstream error wrapping
but not the API contract itself). This closes a named ROADMAP gap.

**Effort to build:** Medium — well-established domain (Google API Design Guide,
JSON:API, OpenAPI conventions), but needs choosing a position rather than
surveying all approaches.

---

### Tier 3 — Ecosystem coverage (framework/tooling specific)

These are valuable for specific tech stacks but less universally applicable.
All are recommended for the optional catalogue; none should be bundled by
default.

---

#### 11. `react-best-practices`

**Description trigger:** Use when writing, reviewing, or optimizing React or
Next.js code — component architecture, hooks rules, server vs. client
components, data fetching patterns, bundle size, and hydration.

**Rationale:** awesomeskill.ai carries a `react-best-practices` skill from
Vercel Engineering (2,306 downloads). The harness has `frameworks/react/CONVENTIONS.md`
as the source-of-truth. Building the harness's own `react-best-practices` skill
from that source (rather than importing awesomeskill.ai's) keeps the single
source-of-truth inside the harness. React/Next.js is the most-used frontend
stack in the harness's target audience.

**Source material:** `frameworks/react/CONVENTIONS.md`,
`languages/typescript/CONVENTIONS.md`

**Effort to build:** Low — content exists; skill is a subset of
`typescript-conventions` + the React-specific layer.

---

#### 12. `database-conventions`

**Description trigger:** Use when designing a database schema, writing
migrations, reviewing SQL queries, or choosing between relational and document
models — covers naming, index strategy, migration safety, N+1 prevention,
and transaction boundaries.

**Rationale:** Database errors (missing indexes, unsafe migrations, unbounded
queries) are among the most common and expensive production bugs. No harness
skill or doc covers this today. Database work is present in every full-stack
project. This would be a net-new piece of content — not wrapping existing
material but adding a genuine new domain.

**Effort to build:** Medium — requires taking a clear position on
PostgreSQL/MySQL dialect differences and ORM vs. raw SQL.

---

#### 13. `docker-conventions`

**Description trigger:** Use when writing a Dockerfile, docker-compose file,
or CI containerization config — multi-stage builds, layer caching, security
(non-root user, minimal base images, no secrets in layers), and health checks.

**Rationale:** Containers are the default deployment unit for harness target
projects. Docker best practices are well-documented but agents frequently
produce insecure or inefficient Dockerfiles (large layers, secrets baked in,
running as root). A skill covering the checklist would directly reduce
production security risk. Aligns with the `security-review` recommendation.

**Effort to build:** Low-medium — well-established domain, content is short
and prescriptive.

---

#### 14. `dependency-audit`

**Description trigger:** Use when adding dependencies, reviewing a project's
dependency tree, or checking for known vulnerabilities — covers `pip-audit`,
`npm audit`, `govulncheck`, lock file hygiene, and update policy.

**Rationale:** Supply-chain security is OWASP Top 10 A06 (Vulnerable and
Outdated Components). The harness's security mandate is stated but no skill
operationalizes it at the dependency level. The tooling (`pip-audit`, `npm audit`,
`govulncheck`) is language-specific and not obvious to agents working in an
unfamiliar stack. This is a short, high-value skill.

**Effort to build:** Low.

---

#### 15. `performance-profiling`

**Description trigger:** Use when diagnosing slow code, high memory usage, or
CPU spikes — language-agnostic profiling workflow: form a hypothesis, identify
the hot path, benchmark before and after changes, interpret profiler output.

**Rationale:** Performance issues are a common agent blind spot — agents
write correct code but not necessarily efficient code. A profiling-oriented
skill would shift agent behavior from "it works" to "it works and is measurably
fast enough." This aligns with the harness's rigor-tier system: production-tier
projects should have a defined performance baseline.

**Effort to build:** Medium — the universal workflow is short; language-specific
tooling references (`cProfile`/`py-spy` for Python, `pprof` for Go,
`perf`/Node's `--inspect` for JS) add some depth.

---

## Priority Summary

| # | Skill | Tier | Source | Effort |
|---|---|---|---|---|
| 1 | `typescript-conventions` | 1 — wrap existing | `languages/typescript/CONVENTIONS.md` | Low |
| 2 | `go-conventions` | 1 — wrap existing | `languages/go/CONVENTIONS.md` | Low |
| 3 | `testing` | 1 — wrap existing | `patterns/testing/` | Medium |
| 4 | `logging` | 1 — wrap existing | `patterns/logging/` | Low |
| 5 | `accessibility` | 1 — wrap existing | `patterns/accessibility/README.md` | Low |
| 6 | `security-review` | 2 — new content | OWASP Top 10, language refs | Medium |
| 7 | `planning-with-files` | 2 — new content (adapt awesomeskill.ai) | awesomeskill.ai pattern | Low–Medium |
| 8 | `requirements-clarification` | 2 — new content | Domain knowledge | Medium |
| 9 | `code-review` | 2 — new content | Domain knowledge | Medium |
| 10 | `api-design` | 2 — new content (ROADMAP) | API design guides | Medium |
| 11 | `react-best-practices` | 3 — ecosystem | `frameworks/react/` | Low |
| 12 | `database-conventions` | 3 — ecosystem | New content | Medium |
| 13 | `docker-conventions` | 3 — ecosystem | New content | Low–Medium |
| 14 | `dependency-audit` | 3 — ecosystem | New content | Low |
| 15 | `performance-profiling` | 3 — ecosystem | New content | Medium |

## Implementation Notes

- **All 15 are recommended as optional** — not bundled by default, available
  via `--skills` at install time. The harness's install system already supports
  selective skill installation.
- **Tier 1 (skills 1–5) should be done first** — they close obvious gaps with
  low effort and no new content decisions.
- **Tier 2 skill 6 (`security-review`) is urgent** — the OWASP mandate in the
  harness's own instructions is currently not backed by actionable skill
  content. This is a safety gap.
- **`planning-with-files` (skill 7)** — the awesomeskill.ai version is open
  source; it should be adapted to match the harness's file/doc conventions
  (`docs/operational/` as the home for agent working docs) rather than imported
  verbatim.
- **None of the Tier 3 skills require a framework or platform to already be
  in the harness** — they are self-contained and can be added incrementally.
- **Skill naming convention** — all use lowercase-with-hyphens to match
  existing skills. The `SKILL.md` frontmatter schema requires `name`,
  `description`, and `metadata.type: skills`.

## Excluded from Consideration

The following awesomeskill.ai skills were considered and excluded as
out-of-scope for a developer-tooling harness:

- `seo-review` (66K downloads) — SEO optimization is a marketing concern, not
  a coding-conventions concern. High downloads reflect web traffic, not
  developer audience fit.
- `content-research-writer` (17K) — Content/blog writing. Not a developer
  workflow.
- `ui-ux-pro-max` (13K) — Opinionated design system. Conflicts with
  `web-design-guidelines`; too prescriptive for a neutral harness.
- `using-superpowers` (20K) — Meta-skill that forces every conversation to
  start with a skill invocation. Invasive; breaks the harness's on-demand
  (description-match) triggering model.
- `notebooklm` — Google-specific tool integration. Not appropriate for a
  general-purpose harness.
- `enterprise-sales` — Not a developer workflow.
- `court-auction-notice-search` — Domain-specific (Korean legal system). Not
  applicable.

---

*Generated 2026-07-14 in worktree `docs/skill-recommendations`.*
*Source data: awesomeskill.ai homepage HTML (2026-07-14), harness file inventory, ROADMAP.md.*
