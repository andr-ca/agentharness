#!/usr/bin/env bash
# PreToolUse guard for Claude Code (wired in .claude/settings.json):
# before a Bash tool call runs `gh pr merge`, require that it go through
# tools/safe-pr-merge.sh instead.
#
# Why this exists. CLAUDE.md's PR-merge checklist is ~60 lines of prose —
# wait for automated review, fetch BOTH comment types, verify each finding
# against current code, reply to every comment, then watch post-merge CI
# to a real terminal state. safe-pr-merge.sh implements all of it, but
# nothing required its use: an agent could call `gh pr merge` directly and
# skip every step, with only the prose standing in the way.
#
# That prose is not decorative. In one week it caught unaddressed review
# comments on three PRs, which surfaced two defects in safe-pr-merge.sh
# itself, a mutex deadlock in agent-lock.sh, and a false-red CI report —
# none of which had a failing test.
#
# The root-instruction inventory (docs/operational/
# root-instruction-inventory-2026-07-28.md) found that mechanical
# enforcement, not size, predicts which router sections are safe to
# compress. This is the "gating beats thinning" move: once the rule is
# enforced here, the prose describing it becomes compressible rather than
# load-bearing.
#
# Exit 0 -> allow the tool call.
# Exit 2 -> block it; stderr is shown to the agent as feedback.
#
# Fails OPEN on anything it cannot parse. A guard that blocked on
# unexpected input would make every Bash call hostage to a payload-shape
# change upstream.
#
# AGENTHARNESS_PR_MERGE_BYPASS=1 overrides, for the case where
# safe-pr-merge.sh itself is broken and the merge must proceed by hand.
# Say why in the PR when you use it.
set -euo pipefail

[ "${AGENTHARNESS_PR_MERGE_BYPASS:-0}" != "1" ] || exit 0

payload="$(cat 2>/dev/null || true)"
cmd="$(printf '%s' "$payload" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print('')
    sys.exit(0)
# Keyed on the PRESENCE of tool_input.command, not on a tool-name
# allowlist. Claude Code calls its shell tool 'Bash', Gemini CLI calls
# it 'run_shell_command', and a name check written against one client
# silently allows everything on the others — the guard would look
# installed and do nothing. Every client that runs a shell command
# passes it as tool_input.command, so that is the portable signal.
command = data.get('tool_input', {}).get('command', '')
print(command if isinstance(command, str) else '')
" 2>/dev/null || true)"

[ -n "$cmd" ] || exit 0

# Tokenize with the shell's own quoting rules rather than stripping
# quotes with a regex. The regex version was subtly wrong: on input like
#   echo "a\" gh pr merge "
# it stripped the wrong span and left an exposed `gh pr merge`, blocking a
# command that only mentions the phrase. shlex knows about escapes,
# nesting and adjacency, and gets the whole class right at once.
#
# The match is then "three CONSECUTIVE tokens", which is exactly the
# instruction-vs-mention distinction wanted:
#   gh pr merge 42              -> ['gh','pr','merge','42']         match
#   echo hi && gh pr merge 42   -> [...,'gh','pr','merge','42']     match
#   echo "run gh pr merge"      -> ['echo','run gh pr merge']       no match
#     (the phrase lives inside ONE token, so it is text, not a command)
if printf '%s' "$cmd" | python3 -c "
import shlex, sys
text = sys.stdin.read()
try:
    tokens = shlex.split(text)
except ValueError:
    # Unbalanced quotes: not something we can reason about. Fail OPEN,
    # consistent with the rest of this guard.
    sys.exit(1)
target = ['gh', 'pr', 'merge']
hit = any(
    tokens[i:i + len(target)] == target
    for i in range(len(tokens) - len(target) + 1)
)
sys.exit(0 if hit else 1)
" 2>/dev/null; then
    cat >&2 <<'MSG'
Blocked: `gh pr merge` bypasses the PR-merge checklist.

Run this instead:
    bash tools/safe-pr-merge.sh <pr-number> [--delete-branch]

It enforces what the checklist requires and a direct merge skips:
  - waits for automated review to post (and stops early if it completed
    with nothing to say)
  - fetches BOTH issue-level and inline review comments
  - refuses to merge while any comment is unanswered
  - polls post-merge CI to a real terminal state, matched by the merge
    commit's SHA

Merge strategy defaults to --merge; pass --squash or --rebase to override.
AGENTHARNESS_PR_MERGE_BYPASS=1 overrides this guard — say why in the PR.
MSG
    exit 2
fi

exit 0
