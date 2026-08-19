# Issue #240 — Cursor/Codex live-verification pass (2026-08-19)

Status: **partial — live-agent verification blocked externally, do not
treat as complete.** Per the issue's own instruction: do not edit
`docs/CLIENT_COMPATIBILITY.md` to "✅ dogfooded" without this note
demonstrating it, and this note does not demonstrate it yet.

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

## What's still open — the actual live-agent verification

None of steps 1–3 above have been run against a real agent session yet.
Blocked externally, not by anything in this repo, as of 2026-08-19:

| Client | Tool | Blocker |
|---|---|---|
| Codex CLI | `codex exec` | Usage limit exhausted; resets 2026-08-23 per the CLI's own error message |
| OpenCode | `opencode run` | Every invocation (including a trivial one outside the fixture) fails with a generic `UnknownError` / "Unexpected server error"; no further detail in `~/.local/share/opencode/log/opencode.log`. Looks like an expired provider auth token, not a fixture problem — not investigated further, out of scope for this repo |
| Cursor | `cursor-agent` | Not logged in yet (operator's own login, in progress separately) |

Regenerate the fixture the moment any one of these clears, from a
checkout at or after `efde74d`:

```
init <target> --mode copy --skills committing,branching,testing
generate-clients <target> --client cursor,codex --force
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

None of this exercises whether Cursor or Codex/OpenCode actually *read
and act on* the generated files in a live session — that's the part
of #240 this note cannot yet close.

## Follow-up

No compatibility-matrix edit made. Re-run this pass (steps 1–3 of the
issue) once at least one of Codex/OpenCode/Cursor is available, and
replace this note's "What's still open" section with the actual
session results before considering #240 done.
