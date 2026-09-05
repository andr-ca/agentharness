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

**Current state — enforced for Python, Go, and JS/TS (`node --test`,
Vitest, or Jest) projects; advisory for everything else.**
`harness-link.sh enforce-profile <project>` reads
`.agentharness-profile` and gates on it for real, at a tier where
`tests.required` is not `false` (prototype skips entirely):

- **Python** (`pyproject.toml`/`setup.py`/`requirements.txt` present):
  runs `pytest --cov-fail-under=<tier's coverage_min>` and fails if it
  doesn't pass.
- **Go** (`go.mod` present): runs `go test -coverprofile ./...` and gates
  the `go tool cover -func` total against the tier's `coverage_min` —
  both standard-toolchain, no third-party dependency.
- **JS/TS** (`package.json` present): a project whose `"test"` script
  invokes Node's built-in `node --test` (per-file coverage summary),
  Vitest, or Jest (both share the same Istanbul-based
  `coverage-summary.json`'s `total.lines.pct`) gets real enforcement —
  the three JS runners with a stable, machine-readable coverage output
  this repo can parse without guessing. Mocha, or anything else, gets a
  clear "not implemented for this runner" and, by default, exits 0.

A project this can't classify at all (no recognizable project file)
gets "not implemented yet" and exits 0 — it never falsely blocks or
falsely passes something it can't actually check. Pass **`--strict`** to
turn every such "not implemented" case into a failure instead, so a CI
job can require that every project it runs against is one enforcement
actually understands.

**Push gate (opt-in).** `--with-coverage-hook` generates a project-owned
`pre-push` that invokes `enforce-profile` against the *consumer*
project — not this harness checkout — on every push (P0-03 / issue
#317). That is the install that makes the coverage floor mechanical.
`--with-hook` alone still only installs trunk protection; silently
changing that default for existing `--with-hook`-only installs is a
breaking-ish decision this repo will not make.

The generated hook calls `enforce-profile` **without** `--strict`.
Unsupported project types and runners (Mocha, unclassified projects)
stay advisory on push (exit 0), matching `enforce-profile`'s default.
`--strict` remains an explicit extra call — pass it when invoking
`enforce-profile` directly (CI, or by hand) if you want unsupported
runners to fail. There is no install-time flag that selects strict for
this hook.

This harness's own `.github/hooks/pre-push` is unchanged: it still only
ever runs *this* repo's hardcoded suites and no-ops for a borrowed
`core.hooksPath` (see the hook's own comments). A copy-mode install
whose recorded `harness-link.sh` path is gone fails the next push with
a clear missing-path message rather than that wrong-repo no-op.

A Mocha adapter remains unimplemented — tracked in `ROADMAP.md` as
P1-02's remaining runner gap.

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
   used when nothing above says otherwise. The mechanical gate
   (`enforce-profile`, including the `--with-coverage-hook` pre-push)
   already defaults to `production` (fail-safe) rather than `internal`
   whenever `.agentharness-profile` is absent or unrecognized — a missing
   or misspelled file must never silently relax enforcement.

## Disabling a profile requirement locally

There's no override flag beyond precedence level 2 above (a repo-local
statement) — if a specific rule genuinely doesn't apply to your project,
say so explicitly in your own `CLAUDE.md` rather than deleting or
downgrading `.agentharness-profile`, so the exception is visible in your
own repo's history and isn't silently inherited by every rule at once.
