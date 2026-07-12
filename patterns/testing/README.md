# Testing

Index for this directory — each doc below is the single source of truth
for its topic; this file doesn't restate their content, just routes to it.

All of it applies in full at the **Production** rigor tier — see
`.github/CODING_GUIDELINES.md#rigor-tiers` and `patterns/profiles/` for
what changes at Prototype/Internal tiers (short answer: tests become
optional or un-gated by a coverage number, not "the same rules apply
everywhere").

| Doc | Covers |
|---|---|
| [TDD.md](./TDD.md) | Red-Green-Refactor workflow, testing pyramid, patterns, worked examples |
| [COVERAGE_REQUIREMENTS.md](./COVERAGE_REQUIREMENTS.md) | The 80% number: what counts, how to measure it per language, handling low coverage |
| [COMPLETION_CHECKLIST.md](./COMPLETION_CHECKLIST.md) | The pre-PR checklist — don't mark work done without running through it |
| [PLAYWRIGHT_UI_TESTING.md](./PLAYWRIGHT_UI_TESTING.md) | Web UI testing: Playwright setup, screenshot verification, browser/responsive coverage |

**Read TDD.md first** if you're new to this repo's testing expectations —
it's the workflow doc; the others are references you'll come back to.
