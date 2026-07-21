#!/usr/bin/env bash
# PreToolUse guard for Claude Code (wired in .claude/settings.json):
# before a Write or Edit tool call lands, verify the target path is
# either inside some git repository's working tree (the main checkout,
# a worktree, a scratch clone) or under the system temp directory (the
# scratchpad every session is told to use for temp files). Anything
# else -- shell rc files, global git config, ~/.config/*, arbitrary
# home-directory files -- gets blocked.
#
# This closes the mechanical half of the "no writes outside the repo"
# gap: an agent once appended an env var to the user's ~/.bashrc while
# trying to persist it for a multi-command shell sequence, instead of
# just exporting it inline. Write/Edit calls are structured (a single
# file_path field), so they can be checked deterministically; Bash
# commands (the actual vector in that incident, via `>>`) are not --
# reliably detecting "this shell command writes outside the repo" is
# not tractable without a high false-positive rate against legitimate
# commands (gh auth setup-git, git worktree add, etc.), so that half of
# the gap is covered by CLAUDE.md's documented mandate instead, not a
# hook.
#
# Exit 0  -> allow the tool call.
# Exit 2  -> block it; stderr is shown to the agent as feedback.
set -euo pipefail

payload="$(cat 2>/dev/null || true)"
tool_name="$(printf '%s' "$payload" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_name', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

case "$tool_name" in
    Write|Edit) ;;
    *) exit 0 ;;
esac

file_path="$(printf '%s' "$payload" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

[ -n "$file_path" ] || exit 0

resolved="$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$file_path" 2>/dev/null || true)"
[ -n "$resolved" ] || exit 0

tmp_root="$(python3 -c "import os, tempfile; print(os.path.realpath(tempfile.gettempdir()))" 2>/dev/null || echo /tmp)"
case "$resolved" in
    "$tmp_root"/*|"$tmp_root") exit 0 ;;
esac

target_dir="$(dirname "$resolved")"
if git -C "$target_dir" rev-parse --show-toplevel >/dev/null 2>&1; then
    exit 0
fi

echo "Blocked: '$file_path' resolves outside any git repository and outside the system temp directory ($tmp_root)." >&2
echo "This is the outside-the-repo write guard (CLAUDE.md File Placement section)." >&2
echo "If the user has explicitly asked for this file, confirm with them first, then use Bash to write it directly." >&2
exit 2
