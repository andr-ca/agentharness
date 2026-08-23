---
date: 2026-08-23
status: completed
topic: research
purpose: Live-verification pass for issue #240's Codex CLI leg — AGENTS.md/skill loading and the PreToolUse guard
related-harness: AGENTS.md, .codex/hooks.json, .github/hooks/claude-pr-merge-guard.sh, docs/CLIENT_COMPATIBILITY.md
---

# Issue #240 — Codex CLI live-verification pass (2026-08-23)

Status: **closed, one leg each way.** The AGENTS.md always-on/on-demand
leg is now live-verified working, the same way Cursor's was on
2026-08-19. The `PreToolUse` guard leg is now live-verified **not**
working — a different and more useful outcome than "still blocked
externally," because it's an actual answer instead of an open question.

## What changed to make this possible

Every prior attempt at this leg (2026-08-19, 2026-08-22) was blocked
before reaching a live agent: Codex's usage limit was exhausted both
times. Checking again on 2026-08-23 (the CLI's own stated reset date)
surfaced a *different* blocker first: `codex login status` reported "Not
logged in," and a trivial `codex exec` call failed with `401
Unauthorized`. This is a harder blocker than a quota wall — no
credential existed at all, not an exhausted one. The operator ran
`codex login` interactively (outside this session, which cannot
complete an OAuth/browser flow on its own) and logged in via ChatGPT.
`codex login status` then reported "Logged in using ChatGPT."

Two smaller frictions surfaced immediately after login, before either
real test could run:

1. **The CLI's model-manifest refresh fails on every invocation**:
   `failed to refresh available models: stream disconnected before
   completion: failed to decode models response: unknown variant "max",
   expected one of "none", "minimal", "low", "medium", "high", "xhigh"`.
   The server now returns a reasoning-level value this installed client
   (`codex-cli 0.115.0`) doesn't know how to parse — the client is
   behind the server's current contract. Cosmetic (the CLI falls back to
   a stale internal model list), but worth recording since it explains
   the next finding.
2. **The default model is rejected for this account type.** `codex exec`
   with no `-m` flag picked `gpt-5.3-codex` from that stale fallback
   list, and the API responded `{"detail":"The 'gpt-5.3-codex' model is
   not supported when using Codex with a ChatGPT account."}`. Passing
   `-m gpt-5.4` (a model actually present in the real, if undecodable,
   manifest) fixed it — a trivial `PONG` echo test then worked. Every
   test below uses `-m gpt-5.4` for this reason.

Neither of these is a defect in this repo — they're properties of the
installed Codex CLI version and this account's plan — but they would
block *any* live Codex session against this repo today without knowing
to add `-m gpt-5.4`, so they're recorded here rather than silently
worked around.

## AGENTS.md always-on load + on-demand skill routing: verified working

Fixture: `init <target> --mode copy --skills committing,branching,testing`
then `generate-clients <target> --client codex --force`, at `main`'s
current HEAD (`7455719`). Same fixture recipe as Cursor's 2026-08-19
pass, same two-fact test:

```
codex exec --sandbox read-only -m gpt-5.4 -C <fixture> \
  "What is the exact shell command to acquire the multi-agent lock, \
   and what is the exact TDD cycle name this project uses?"
```

Response:

> The exact lock command shown is:
> ```bash
> tools/agent-lock.sh acquire "<feature>" "<branch>"
> ```
> The exact TDD cycle name shown is:
> `Red-Green-Refactor`

Both are exact matches. The lock command exists only in `AGENTS.md`'s
router content (not in any of the fixture's 3 installed skills); the
TDD cycle name exists only in `.agents/skills/testing/SKILL.md` (not in
the router or the other two skills). Confirmed by direct inspection of
the fixture, same isolation method used for Cursor. **Nothing failed.**
No follow-up bugs to file for this leg.

## `PreToolUse` guard: verified NOT working

Fixture: a bare `git init` outside this repo, with only `.codex/hooks.json`
and `.github/hooks/claude-pr-merge-guard.sh` copied in — mirroring the
throwaway fixture used for Cursor's guard test in PR #267.

**First attempt** (`--sandbox workspace-write`, default model rejection
already fixed via `-m gpt-5.4`): Codex's own OS-level sandbox
(`bwrap`) failed before `gh` even started — `bwrap: loopback: Failed
RTM_NEWADDR: Operation not permitted`. This is a nested-sandboxing
artifact of running inside this session's own sandboxed environment,
not a signal about the guard one way or the other. Retried with
`--sandbox danger-full-access` (a documented Codex sandbox policy,
not the `--dangerously-bypass-approvals-and-sandbox` mega-flag) to get
past it.

**Second attempt** (`--sandbox danger-full-access`): the command
actually ran this time. `gh pr merge 1` executed and failed only on its
own missing-remote error (`no git remotes found` / `no git remotes
found in ...`) — **the guard never fired.** No blocking message, no
guard `stderr` text, nothing. This is the actual finding: not "blocked
by something else," but "ran straight through."

**Root cause, confirmed via `codex features list`:**

```
codex_hooks                      under development  false
```

`codex_hooks` — the feature gate for Codex's own hook-execution runtime
— ships disabled by default in `codex-cli 0.115.0`. Forcing it on
(`codex exec --enable codex_hooks ...`) does take effect —
`codex features list --enable codex_hooks` confirms the override flips
the reported state to `true`, and the exec run prints the CLI's own
warning: `"Under-development features enabled: codex_hooks.
Under-development features are incomplete and may behave
unexpectedly."` — but the guard **still** didn't fire. A third attempt
with `RUST_LOG=debug --enable codex_hooks --sandbox danger-full-access`
confirms why: the debug log shows `CodexHooks` present in the active
feature list (`features=[ShellTool, UnifiedExec, CodexHooks,
ShellSnapshot, Sqlite, EnableRequestCompression, ...]`), but contains
**zero** log lines anywhere about loading `.codex/hooks.json`,
matching a `PreToolUse` hook, or executing one. `gh pr merge 1` ran
unblocked in this configuration too, failing only on the same
missing-remote error as before.

**Conclusion:** the config surface Codex documents (and this repo
ported) is real and correctly formed — `.codex/hooks.json` parses
without error (the 2026-08-22 parse-bug fix from #264 holds). But the
client-side runtime that would actually read that file and act on it
during a shell-tool call does not exist yet in this installed version,
even when its own feature flag is explicitly forced on. This is a
Codex CLI limitation, not a defect in this repo's port — there is
nothing to fix here beyond documenting it accurately, which
`docs/CLIENT_COMPATIBILITY.md` and `.codex/hooks.json`'s own
`description` field now do.

## What this means for #240 and #229

#240's Codex leg is now **closed** — both halves have a real, dated
answer instead of "blocked externally." #229 (qwen support), gated on
"two existing non-Claude adapters have dated live-session notes," now
has its second adapter: Cursor (2026-08-19/2026-08-22) plus Codex
(2026-08-23, this note) satisfy that gate on the AGENTS.md-loading
half, which is the half every AGENTS.md-family client (including qwen)
actually shares. The guard-blocking half remains open only for Codex
specifically (and still-unattempted for Gemini/OpenCode), and is a
Codex-CLI-version limitation rather than a repo gap.

## Follow-up

- `docs/CLIENT_COMPATIBILITY.md`'s Codex rows updated: `AGENTS.md` row
  now ✅ live-verified 2026-08-23; `PreToolUse` row changed from ⚠️
  (config loads, unverified) to ❌ (confirmed non-functional), with the
  narrative section carrying the full finding.
- `.codex/hooks.json`'s `description` field carries a standing warning
  so a future session doesn't have to rediscover this from scratch.
- No code fix needed or possible from this repo's side — re-check once
  a newer Codex CLI version ships (watch for `codex_hooks` moving out of
  "under development" in `codex features list`, or the model-manifest
  parse error clearing, which would suggest a client update happened).
