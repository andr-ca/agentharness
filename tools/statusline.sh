#!/usr/bin/env bash
# statusline.sh — Claude Code status line: harness state at a glance.
#
# Reads the session JSON Claude Code pipes on stdin (see
# https://code.claude.com/docs/en/statusline) and prints one line combining
# baseline session info (model, directory, branch, context usage) with
# harness-specific state this repo uniquely knows about: publish-authority
# mode and whether the current branch is locked by another agent session.
#
# Installed via `harness-link.sh init/update --with-statusline`, which wires
# it into .claude/settings.json's `statusLine`. Safe to run standalone for a
# quick check: echo '{}' | tools/statusline.sh
#
# The authority summary here is a best-effort glance, not an authoritative
# decision — it counts active (non-expired, non-revoked) grants without
# resolving target-branch globs. For an authoritative per-branch answer use
# `agentharness authority check --operation <op> --target <branch>`.
set -euo pipefail

session_json="$(cat)"

parsed="$(STATUSLINE_SESSION_JSON="$session_json" python3 - <<'PYEOF'
import json
import os

try:
    data = json.loads(os.environ.get("STATUSLINE_SESSION_JSON") or "{}")
except json.JSONDecodeError:
    data = {}

model = (data.get("model") or {}).get("display_name") or "?"
workspace = data.get("workspace") or {}
directory = workspace.get("current_dir") or data.get("cwd") or "."
ctx = data.get("context_window") or {}
pct = ctx.get("used_percentage")
pct_str = f"{int(pct)}%" if isinstance(pct, (int, float)) else "?"

# Tab-separated: none of these fields legitimately contain a literal tab.
print(f"{model}\t{directory}\t{pct_str}")
PYEOF
)"

IFS=$'\t' read -r model directory context_pct <<<"$parsed"

repo_root=""
branch=""
if repo_root="$(git -C "$directory" rev-parse --show-toplevel 2>/dev/null)"; then
    branch="$(git -C "$repo_root" symbolic-ref --short HEAD 2>/dev/null || true)"
    if [ -z "$branch" ]; then
        branch="$(git -C "$repo_root" rev-parse --short HEAD 2>/dev/null || echo "detached")"
    fi
fi

authority="stage-only"
if [ -n "$repo_root" ]; then
    if [ -f "$repo_root/.agentharness-authority.json" ]; then
        authority="$(AUTHORITY_FILE="$repo_root/.agentharness-authority.json" python3 - <<'PYEOF'
import json
import os
from datetime import datetime, timezone

path = os.environ["AUTHORITY_FILE"]
try:
    with open(path) as f:
        contract = json.load(f)
except (OSError, json.JSONDecodeError):
    print("scoped(?)")
    raise SystemExit

grants = contract.get("grants") or []
revoked = set(contract.get("revoked") or [])
now = datetime.now(timezone.utc)


def parse_expiry(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    # A naive datetime (no offset in the ISO string) can't be compared
    # against the timezone-aware `now` below without raising TypeError —
    # treat it as UTC rather than let that crash the whole statusline.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


active = []
for grant in grants:
    ops = [op for op in (grant.get("operations") or []) if op not in revoked]
    if not ops:
        continue
    expires = parse_expiry(grant.get("expires"))
    if expires is not None and expires <= now:
        continue
    active.append((grant, expires))

if not active:
    print("scoped(none active)")
else:
    expiries = [exp for _, exp in active if exp is not None]
    if expiries:
        soonest = min(expiries)
        hours_left = int((soonest - now).total_seconds() // 3600)
        print(f"scoped({len(active)}, ~{hours_left}h left)")
    else:
        print(f"scoped({len(active)})")
PYEOF
)"
    elif [ -f "$repo_root/.agentharness-publish-mode" ]; then
        authority="full-publish"
    fi
fi

lock_info=""
if [ -n "$repo_root" ] && [ -n "$branch" ] && [ -x "$repo_root/tools/agent-lock.sh" ]; then
    if "$repo_root/tools/agent-lock.sh" check-branch "$branch" >/dev/null 2>&1; then
        lock_info="unlocked"
    else
        lock_info="locked-by-other"
    fi
fi

line="[$model] $(basename "$directory")"
[ -n "$branch" ] && line+=" ($branch)"
line+=" ctx:$context_pct | $authority"
[ -n "$lock_info" ] && line+=" | $lock_info"

printf '%s\n' "$line"
