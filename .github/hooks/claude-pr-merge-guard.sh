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
if data.get('tool_name') != 'Bash':
    print('')
    sys.exit(0)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || true)"

[ -n "$cmd" ] || exit 0

# Strip quoted spans before matching, so discussing the rule in an echo or
# a commit message does not trip it — the same principle the force-push
# documentation check follows. Without this, replying to a review comment
# about `gh pr merge` would be blocked.
unquoted="$(printf '%s' "$cmd" | python3 -c "
import re, sys
text = sys.stdin.read()
text = re.sub(r'\"[^\"]*\"', ' ', text)
text = re.sub(r\"'[^']*'\", ' ', text)
print(text)
" 2>/dev/null || printf '%s' "$cmd")"

# Word-boundary match on the subcommand, so 'gh pr merge' is caught
# anywhere in a compound command while 'gh pr view'/'checks'/'comment'
# are not. safe-pr-merge.sh's own internal call runs in a separate
# process and never passes through this hook.
if printf '%s' "$unquoted" | grep -qE '(^|[;&|[:space:]])gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
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
