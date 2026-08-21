# Known Limitations

The current, honest list of **what to expect *not* to work yet**, in one
place — the companion to [STATUS.md](./STATUS.md) (what *does* work).
This is a curated summary of open gaps; the full planned-vs-built
breakdown, with proposals and this-review's numbering, lives in
[ROADMAP.md](../ROADMAP.md). Where a gap is tracked there, the label is
noted — resolve any label against the review filename cited next to it in
[ROADMAP.md](../ROADMAP.md), since two review rounds reused the same
`P1-xx`/`P2-xx` numbers.

## Verification & evidence

- **Not verified against live tool sessions (except Claude Code).** Every
  generated adapter (`AGENTS.md`, `GEMINI.md`,
  `.github/copilot-instructions.md`, `.cursor/rules/`, `.kilo/rules/`)
  and every custom-agent port is implemented against each tool's
  *published* behavior, not dogfooded end-to-end. See
  [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s intro and
  [DECISIONS.md](./DECISIONS.md)'s "Claude-first client scope".
- **Dogfood is real but not independent.** No longer "fixtures only": the
  harness has been installed and used in non-fixture repositories
  (`andr-ca/recalium`, `andr-ca/infoocode`), and that use has produced
  real friction filed upstream as issues — #76, #77, #78, #79, #88, #149
  (recalium) and #110, #117 (infoocode). What remains open is the part
  that matters most for generalization: **every one of those repos is the
  author's own**, so correlated blind spots are untested, and none of the
  systematic signals `docs/operational/planning/DOGFOODING.md` asks for
  (install time, overrides needed, false-positive rate, update friction,
  context cost, abandoned features) has been recorded in a dated dogfood
  status doc. → ROADMAP "P2-05 (real dogfood)" / P2-02.
- **Evals now have first evidence for enforcement, none for code
  quality.** Live baseline/treatment runs exist and are written up in
  `docs/operational/eval-harness-observations-2026-07-23.md`: governed-action
  safety was measured deterministically from git state, with trunk
  commits going 2/2 unsafe → 0/2 under enforcement, and branch-first
  behavior going 0/9 → 3/3 from the advisory layer alone (all hooks off).
  Treat these as integration tests for the boundary, **not** as
  statistics: single-digit run counts, one to three governed actions, and
  a driver that is neither the target client nor a frontier model — the
  runs used the `opencode` CLI on the free `opencode/big-pickle` model,
  not Claude Code with its Stop-hook completion gate, which is the client
  the harness actually targets and the one whose enforcement surface is
  widest. The code-correctness battery read flat, and that flat
  result is a measurement artifact — toy tasks a capable model aces
  either way — not evidence the harness is inert. No run has shown the
  harness improves code quality, and none has been run on the target
  agent. → ROADMAP P2-01, P2-03.

## Enforcement

- **Profile enforcement is partial.** `harness-link.sh enforce-profile`
  gates for real on Python, Go, and `node --test`/Vitest/Jest JS/TS
  projects; Mocha and unrecognized project types are advisory (exit 0,
  or fail under `--strict`). It is also **not wired into the pre-push
  hook** — it ships as an explicitly-invoked subcommand. → ROADMAP P1-02.

## Runtime upgrades

- **Verified candidate execution is Linux-only.** Runtime artifacts are built
  and authenticated for both Linux and Darwin, but `runtime plan-upgrade`
  rejects candidate execution on Darwin before launching candidate code.
  macOS `sandbox-exec` can deny network and host writes, but the available
  process resource limits do not provide the enforceable address-space bound
  required by this trust boundary; `RLIMIT_DATA` is not a substitute because
  memory mappings bypass it. Use a Linux host for verified upgrade planning.

## Client integration

- **Client-adapter generation isn't wired into `init`/`update` yet.**
  `harness-link.sh generate-clients <project> --client all` now produces
  the router/instruction files in one command, but generation is still a
  separate step from `init`/`update`, and generated files aren't tracked
  in state for `doctor`/`uninstall` via managed blocks. → ROADMAP P1-01
  (first increment shipped; managed-block lifecycle integration open).
- **Custom sub-agent tool/permission scoping is not ported.** The
  agent generators carry `name`/`description`/`model` and the body
  verbatim, but not Claude Code's `tools:` allow-list or any target
  tool's own permission vocabulary — re-specify those by hand per
  platform. See [CLIENT_COMPATIBILITY.md](./CLIENT_COMPATIBILITY.md)'s
  custom-agent table.

## Content coverage

- **Languages:** Python, TypeScript, Go, and Rust. Java and others are
  not started. → ROADMAP "Planned Components".
- **Frameworks:** only React. Vue/Angular/Django/Express/etc. are not
  started.
- **Patterns:** no graphql pattern, no messaging pattern, and no caching
  pattern yet. → ROADMAP "Planned Components". (Phrased as separate
  `no <name> pattern` clauses on purpose — that is the form
  `check_absence_claims_match_manifest()` parses, so each claim is
  checked against `manifest.yaml` instead of just read by a human.)

## Maintenance & robustness

- **Review history isn't archived yet.** This file and
  [STATUS.md](./STATUS.md) are the first step of consolidating the long
  dated review chain under [docs/operational/reviews/](./operational/reviews/);
  moving completed cycles into dated archive directories is still open.
  → ROADMAP P1-10.
- **Managed state has no migration contract.** `.agentharness-state.json`
  declares `version: 1` with no forward-migration machinery or
  cross-version test matrix. → ROADMAP P1-09.
- **Package materialization is coupled to writable Git metadata.**
  `materialize-skill-symlinks.py restore` uses `git checkout`, so it
  fails in a restricted/non-Git source package. → ROADMAP P1-04.
