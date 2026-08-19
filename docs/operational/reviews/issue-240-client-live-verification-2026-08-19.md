# Issue #240 — Cursor/Codex live-verification pass (2026-08-19)

Status: **partial.** Cursor's leg is now live-verified (below); the
`AGENTS.md`-client leg (Codex/OpenCode) is still blocked externally. Per
the issue's own instruction: don't mark a client "✅ dogfooded" in
`docs/CLIENT_COMPATIBILITY.md` without a note demonstrating it — the two
Cursor rows there now link back to this note; every other row is
unchanged.

## What the issue asked for

1. Fresh consumer project, `init` + `generate-clients --client cursor`
   (or `all`).
2. Open it in Cursor. Confirm the always-on router loads, at least two
   on-demand rules fire when relevant, and the `coding-guidelines-reviewer`
   subagent is invocable if Cursor still exposes that feature.
3. Repeat for one `AGENTS.md` client.
4. Write this note: what loaded, what didn't, overrides needed, context
   cost if measurable.
5. File follow-up bugs for anything that failed.

Plus a CI cousin: run the client generators twice at the same SHA and
assert byte-identical output.

## What actually happened

Setting up the fixture for step 1–3 (a project `init`'d with
`--skills committing,branching,testing`, then `generate-clients --client
cursor,codex`) surfaced three real, compounding defects that made
`generate-clients` non-functional or wrong for **any** real consumer
install — none of which were about live-agent behavior, all of which
were found before a live agent was ever invoked:

1. **`generate-clients`/`audit-prs` were unreachable through the
   published npm CLI.** `bin/cli.js` injected a bogus `--mode npm` into
   any subcommand it didn't recognize, and both were missing from its
   known-subcommand list.
2. **Even with routing fixed, the npm package never shipped the
   generator scripts `generate-clients` needs** (`tools/generate-*.sh`,
   `tools/lib/adapter-common.sh`) — only the dispatcher
   (`harness-link.sh`) was in `package.json`'s `files` allowlist.
3. **Every generated client file listed the harness's entire skill
   catalog, not the consumer's installed subset.** All five generators
   computed their skill index from the harness's own `.claude/skills/`
   regardless of the output target. Worst for Cursor: a project init'd
   with 3 skills still got ~30 `.mdc` rule files, 27 pointing at skills
   that don't exist in the project. A first version of the fix missed a
   nested-output-path case (`generate-kilo-rules.sh`'s `--output` lands
   two directories below the project root, not one) — caught by
   Copilot's review on the fix PR, reproduced, and fixed.

All three are fixed, tested (each regression test verified to fail
against the unfixed source and pass against the fix), and merged —
[PR #243](https://github.com/andr-ca/agentharness/pull/243), post-merge
CI on `main` green.

**The reproducibility CI cousin already existed** before this issue was
filed: `tools/tests/generate-clients.bats:69`
("`is idempotent — a second run reproduces identical files`", from
PR #66, 2026-07-13) runs `generate-clients` twice against the same
target at the same SHA and hashes every file for equality. It already
runs in CI's `content-quality` job. No new work needed there.

## Cursor live verification (2026-08-19)

Cursor has no headless CLI in the traditional sense; used `cursor-agent
--print --mode ask --trust` (Cursor's own non-interactive agent CLI —
`--mode ask` is read-only, so this could only answer from what it
loaded, not edit anything) against a fixture built with `init --mode
copy --skills committing,branching,testing` then `generate-clients
--client cursor` at `main`'s HEAD (post-#243/#244).

**Always-on router** (`agentharness-router.mdc`, `alwaysApply: true`):
prompted for the exact completion-gate command and the exact
multi-agent-lock-acquire command — both harness-specific enough that a
generic model has no way to guess them. Response:

> Completion gate: `bash tools/check-completion.sh`
> Lock: `tools/agent-lock.sh acquire "<feature>" "<branch>"` (export the
> printed id as `AGENTHARNESS_AGENT_ID`)

Exact match to the router's own text. Router confirmed loading.

**On-demand rules** (2, as the issue asked for at least two): the same
prompt also asked for the branch naming convention — content that
exists only in `branching.mdc`, not the router (confirmed:
`grep -c '{type}/{description}' agentharness-router.mdc` → 0,
`branching.mdc` → 1). Response:

> Branches: `{type}/{description}` — lowercase, hyphens (e.g.
> `feature/user-authentication`, `fix/email-validation-crash`)

A second, separate prompt asked for the TDD cycle name used in this
project — content that exists only in `testing.mdc`. Response:

> **Red-Green-Refactor.** Red = a failing test for one new behavior;
> Green = the smallest change that makes it pass; Refactor = clean up
> while tests stay green.

Both on-demand rules fired correctly on relevant prompts, with no
`globs` set (Agent-Requested activation, matched by `description`).

**`coding-guidelines-reviewer` subagent invocability:** not tested —
out of scope for this pass. `generate-clients` does not port custom
subagents at all (that's `tools/generate-cursor-agents.sh`, a separate,
unrelated script family the issue's proposed shape didn't distinguish
from the skill-rule generator). Confirmed by reading
`cmd_generate_clients` in `tools/setup/harness-link.sh`: its
`--client cursor` case only ever calls `generate-cursor-rules.sh`.

**Overrides needed:** none for the router or skill content itself.
`--trust` was required to run `cursor-agent` non-interactively against
an unfamiliar directory — expected first-run behavior for any tool
with shell/write access, not a harness-specific friction point.

**Context cost:** not measured — `cursor-agent --print` doesn't expose
per-rule token accounting the way `codex exec`'s session summary would.

**Nothing failed.** No follow-up bugs to file for the Cursor leg.

## What's still open — the AGENTS.md-client leg

Steps 1–3 have not been run against a real Codex or OpenCode session.
Blocked externally, not by anything in this repo, as of 2026-08-19:

| Client | Tool | Blocker |
|---|---|---|
| Codex CLI | `codex exec` | Usage limit exhausted; resets 2026-08-23 per the CLI's own error message |
| OpenCode | `opencode run` | Every invocation (including a trivial one outside the fixture) fails with a generic `UnknownError` / "Unexpected server error"; no further detail in `~/.local/share/opencode/log/opencode.log`. Looks like an expired provider auth token, not a fixture problem — not investigated further, out of scope for this repo |

Regenerate the fixture the moment either clears, from a checkout at or
after `efde74d`:

```
init <target> --mode copy --skills committing,branching,testing
generate-clients <target> --client codex --force
```

## Static verification done so far (not a substitute for the above)

- `AGENTS.md`'s skill index, after the fix, lists exactly the 3
  installed skills and nothing else; verified by direct inspection of
  the fixture and by `tools/tests/generate-agents-md.bats`'s new
  targeted regression test.
- `.cursor/rules/` contains exactly 4 files (router + 3 installed
  skills) instead of the pre-fix 36.
- The harness's own self-dogfooded `AGENTS.md`/`GEMINI.md`/Kilo output
  is byte-identical before and after every fix in this pass (diffed
  directly against the committed files).

None of this exercises whether a live agent actually *reads and acts
on* the generated files — that's what the Cursor section above now
does close, and what the Codex/OpenCode leg still doesn't.

## Follow-up

`docs/CLIENT_COMPATIBILITY.md`'s two Cursor rows (always-on router,
on-demand skills) now say "live-verified 2026-08-19" and link here — no
other row was touched. Re-run steps 1–3 against Codex or OpenCode once
either is available, and update this note plus the corresponding
`AGENTS.md`-client rows before considering #240 done.
