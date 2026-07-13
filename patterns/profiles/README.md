# Rigor-Tier Profiles

`.github/CODING_GUIDELINES.md#rigor-tiers` describes three tiers in
prose. The files in this directory are the same three tiers as
machine-readable YAML — `prototype.yaml`, `internal.yaml`,
`production.yaml` — so a project (or a script) can *select* a tier
instead of an agent re-reading and re-interpreting a table every time.

The YAML files are the source of truth for which values apply; the
prose table remains the source of truth for *why* — don't let the two
drift apart, update both together.

## Selecting a profile

A project declares its tier by creating a one-line `.agentharness-profile`
file at its repo root, containing exactly one of `prototype`, `internal`,
or `production`:

```bash
echo production > .agentharness-profile
```

<<<<<<< HEAD
**Current state — this is advisory, not (yet) enforced.** No script in
this repo reads `.agentharness-profile` today. `.github/hooks/pre-push`
would be the natural place to enforce it, but that hook currently only
ever runs *this* repo's own hardcoded test suites — it no-ops entirely
for a consumer's push (see the hook's own comments and
`docs/operational/reviews/gpt-5.6-review-status.md`, finding 1) — and
agentharness itself should always stay `production` tier, so wiring the
hook to read a profile file wouldn't change anything real yet. That
wiring belongs with whatever eventually teaches the hook to discover and
run a *consumer's own* test suite (see `ROADMAP.md` / P1-04's lifecycle
CLI) — tracked there rather than built here as enforcement with nothing
real to enforce.

Until then, these YAML files are a lookup a project or an agent can
consult directly instead of re-parsing the prose table — a real
improvement over prose-only tiers, just not a mechanical gate.
=======
**Current state — enforced for Python projects, advisory for everything
else.** `harness-link.sh enforce-profile <project>` (B4) reads
`.agentharness-profile` and, for a detected Python project
(`pyproject.toml`/`setup.py`/`requirements.txt` present), actually gates
on it: skips the test run entirely at a tier where `tests.required` is
`false` (prototype), otherwise runs
`pytest --cov-fail-under=<tier's coverage_min>` for real and fails if it
doesn't pass. A project this can't yet classify (non-Python, or no
recognizable project file) gets a clear "not implemented yet" and exits
0 — it never falsely blocks or falsely passes something it can't
actually check.

This is **not** wired into `.github/hooks/pre-push` automatically —
that hook still only ever runs *this* repo's own hardcoded test suites
and no-ops for a consumer's push (see the hook's own comments and
`docs/operational/reviews/gpt-5.6-review-status.md`, finding 1).
Silently changing that default for every project that already has
`--with-hook` installed is its own decision; `enforce-profile` ships
first as an explicitly-invoked subcommand, same posture as
`audit`/`doctor`, so a project or CI job opts in by calling it.

Non-Python profile enforcement (Go, TypeScript, etc.) remains
unimplemented — tracked in `ROADMAP.md` as a natural extension once this
Python v1 has real usage to learn from.
>>>>>>> origin/main

## Precedence order

When a rule in the Rigor Tiers table could apply at more than one level,
higher wins:

1. **Explicit instruction in the current request** — a human saying
   "treat this as production tier" (or naming a specific bar like "add
   tests for this") overrides everything below, for that request only.
2. **A repo-local override** — a project's own `CLAUDE.md` or equivalent
   stating a different tier for a specific directory or module (e.g. "the
   `scripts/` directory stays prototype tier even though the rest of this
   repo is production").
3. **The profile selected via `.agentharness-profile`.**
4. **Language/framework-specific add-on guidance** — e.g.
   `languages/python/CONVENTIONS.md` — where it's more specific than the
   generic tier table for that language.
5. **The generic default** — the Rigor Tiers table's `internal` column,
   used when nothing above says otherwise. If profile selection is ever
   wired into a mechanical gate (see "Current state" above), that gate
   must default to `production` (fail-safe) rather than `internal`
   whenever `.agentharness-profile` is absent or unrecognized — a missing
   or misspelled file must never silently relax enforcement.

## Disabling a profile requirement locally

There's no override flag beyond precedence level 2 above (a repo-local
statement) — if a specific rule genuinely doesn't apply to your project,
say so explicitly in your own `CLAUDE.md` rather than deleting or
downgrading `.agentharness-profile`, so the exception is visible in your
own repo's history and isn't silently inherited by every rule at once.
