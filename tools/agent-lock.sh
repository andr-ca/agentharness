#!/usr/bin/env bash
# agent-lock.sh — per-feature lock file management for concurrent agent sessions.
#
# Usage:
#   tools/agent-lock.sh acquire <feature> <branch> [worktree]
#   tools/agent-lock.sh release <feature> [agent_id]  (defaults to $AGENTHARNESS_AGENT_ID)
#   tools/agent-lock.sh check   <feature>
#   tools/agent-lock.sh check-branch <branch>
#   tools/agent-lock.sh list
#   tools/agent-lock.sh clean
#   tools/agent-lock.sh suggest-branch <feature>
#
# See patterns/multi-agent-coordination/COORDINATION.md for the full protocol.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${AGENTHARNESS_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
LOCKS_DIR="$REPO_ROOT/.agentharness-locks"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_slug() {
    local feature="$1"
    local trimmed
    trimmed="$(echo "$feature" | tr '[:upper:]' '[:lower:]' | tr ' /' '-' | cut -c1-40)"
    local hash
    hash="$(printf '%s' "$feature" | sha256sum | cut -c1-8)"
    echo "${trimmed}-${hash}"
}

_lock_path() {
    echo "$LOCKS_DIR/$(_slug "$1").json"
}

_pid_start_epoch() {
    # Best-effort: the recorded pid's own process-start time, in epoch
    # seconds, or empty if undeterminable (unsupported ps, permission
    # denied, process already gone). `ps -o lstart=` is supported by both
    # GNU (Linux) and BSD (macOS) ps and prints a ctime-style string; the
    # single-digit-day case pads with an extra space ("Jan  1"), which the
    # whitespace normalization below collapses before parsing.
    local pid="$1"
    local lstart
    lstart="$(ps -o lstart= -p "$pid" 2>/dev/null || true)"
    [[ -n "$lstart" ]] || return 0
    python3 -c "
import sys
from datetime import datetime
raw = ' '.join(sys.argv[1].split())
try:
    print(int(datetime.strptime(raw, '%a %b %d %H:%M:%S %Y').timestamp()))
except ValueError:
    pass
" "$lstart" 2>/dev/null || true
}

_is_stale() {
    # A lock is stale if its recorded pid is dead, OR if that pid is alive
    # but its CURRENT process-start time no longer matches the start time
    # recorded at acquire time — meaning the OS has since reused the pid
    # number for an unrelated process (#148: a merged, week-old lock read
    # as "live" indefinitely because kill -0 happened to match an
    # unrelated long-running process that now occupies the same pid).
    #
    # $2 (recorded_pid_started_at) is optional: pre-existing lock files
    # written before this field existed, or a pid whose start time
    # couldn't be determined at acquire time, have no value to compare
    # against — fall back to the original kill-0-only check rather than
    # risk a false "stale" from an unverifiable comparison.
    local pid="$1"
    local recorded_pid_started_at="${2:-}"
    if ! kill -0 "$pid" 2>/dev/null; then
        return 0  # stale: process is dead
    fi
    if [[ -n "$recorded_pid_started_at" ]]; then
        local current_pid_started_at
        current_pid_started_at="$(_pid_start_epoch "$pid")"
        if [[ -n "$current_pid_started_at" ]] && [[ "$current_pid_started_at" != "$recorded_pid_started_at" ]]; then
            return 0  # stale: pid was reused by a different process
        fi
    fi
    return 1  # still alive, same process that acquired the lock
}

_is_ancestor_pid() {
    # Is $1 an ancestor of this process? Lets a session recognize its own
    # lock without exporting AGENTHARNESS_AGENT_ID: the pid recorded at
    # acquire time (the session's long-lived parent) is an ancestor of
    # every later shell that session spawns.
    local target="$1"
    local cur=$$
    while [[ "$cur" -gt 1 ]]; do
        if [[ "$cur" -eq "$target" ]]; then
            return 0
        fi
        cur="$(ps -o ppid= -p "$cur" 2>/dev/null | tr -d '[:space:]')"
        [[ -n "$cur" ]] || return 1
    done
    return 1
}

_make_agent_id() {
    # Use /proc/sys/kernel/random/uuid when available, else Python fallback
    if [[ -r /proc/sys/kernel/random/uuid ]]; then
        cat /proc/sys/kernel/random/uuid
    else
        python3 -c "import uuid; print(uuid.uuid4())"
    fi
}

_atomic_write() {
    local target="$1"
    local content="$2"
    local tmp
    tmp="$(mktemp "$LOCKS_DIR/.tmp-XXXXXX.json")"
    trap 'rm -f "$tmp"' EXIT
    printf '%s\n' "$content" > "$tmp"
    mv "$tmp" "$target"
    trap - EXIT
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_acquire() {
    local feature="${1:-}"
    local branch="${2:-}"
    local worktree="${3:-null}"

    if [[ -z "$feature" || -z "$branch" ]]; then
        echo "Usage: tools/agent-lock.sh acquire <feature> <branch> [worktree]" >&2
        return 1
    fi

    mkdir -p "$LOCKS_DIR"
    local path
    path="$(_lock_path "$feature")"
    local mutex_dir
    mutex_dir="$LOCKS_DIR/.mutex-$(_slug "$feature")"

    # Best-effort atomic acquire: mkdir is atomic on POSIX filesystems
    if ! mkdir "$mutex_dir" 2>/dev/null; then
        # Another process holds the mutex — wait briefly and retry once
        sleep 0.1
        mkdir "$mutex_dir" 2>/dev/null || { echo "RACE: could not acquire mutex — retry" >&2; return 1; }
    fi
    trap 'rmdir "$mutex_dir" 2>/dev/null' EXIT

    if [[ -f "$path" ]]; then
        local pid pid_started_at
        pid="$(python3 -c "import json,sys; d=json.load(open('$path')); print(d['pid'])" 2>/dev/null || echo "0")"
        pid_started_at="$(python3 -c "import json,sys; d=json.load(open('$path')); print(d.get('pid_started_at') or '')" 2>/dev/null || echo "")"
        if [[ "$pid" -gt 0 ]] && ! _is_stale "$pid" "$pid_started_at"; then
            echo "LOCKED: '$feature' is already being worked on." >&2
            python3 -c "
import json, sys
d = json.load(open('$path'))
print(f\"  agent_id : {d['agent_id']}\")
print(f\"  branch   : {d['branch']}\")
print(f\"  worktree : {d.get('worktree', 'none')}\")
print(f\"  since    : {d['started_at']}\")
print()
print('Options:')
print('  1. Wait for the agent to finish and release the lock.')
print(f\"  2. Create your own branch: git worktree add -b feat/{d['branch']}-2 .worktrees/alt main\")
" >&2
            return 1
        fi
        # Stale lock — remove it
        rm -f "$path"
    fi

    local agent_id
    agent_id="$(_make_agent_id)"
    local started_at
    started_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    local pid="${AGENT_LOCK_PID:-$PPID}"
    # Recorded once, at acquire time, so later liveness checks can tell a
    # still-running owner from an unrelated process that later reused this
    # exact pid number (#148) — empty/null if undeterminable on this
    # platform, in which case staleness checks fall back to kill-0 only.
    local pid_started_at
    pid_started_at="$(_pid_start_epoch "$pid")"

    local worktree_val
    if [[ "$worktree" == "null" ]]; then
        worktree_val="None"
    else
        worktree_val="'$worktree'"
    fi

    local pid_started_at_val
    if [[ -n "$pid_started_at" ]]; then
        pid_started_at_val="$pid_started_at"
    else
        pid_started_at_val="None"
    fi

    local content
    content="$(python3 - <<HEREDOC
import json, sys
print(json.dumps({
    "agent_id":        "$agent_id",
    "feature":         "$feature",
    "branch":          "$branch",
    "worktree":        $worktree_val,
    "started_at":      "$started_at",
    "pid":             $pid,
    "pid_started_at":  $pid_started_at_val,
}, indent=2, sort_keys=True))
HEREDOC
)"

    _atomic_write "$path" "$content"
    rmdir "$mutex_dir" 2>/dev/null
    trap - EXIT
    echo "ACQUIRED: locked '$feature' (agent_id=$agent_id)" >&2
    echo "$agent_id"
}

cmd_release() {
    local feature="${1:-}"
    # Falls back to AGENTHARNESS_AGENT_ID (which the protocol already
    # mandates exporting after acquire) so the id doesn't have to be
    # re-typed positionally at release time, often long after acquire ran.
    local agent_id="${2:-${AGENTHARNESS_AGENT_ID:-}}"

    if [[ -z "$feature" || -z "$agent_id" ]]; then
        echo "Usage: tools/agent-lock.sh release <feature> <agent_id>" >&2
        echo "  <agent_id> is the value printed by acquire, exported as AGENTHARNESS_AGENT_ID" >&2
        return 1
    fi

    local path
    path="$(_lock_path "$feature")"
    if [[ ! -f "$path" ]]; then
        echo "NOT FOUND: no lock for '$feature'" >&2
        return 1
    fi

    local lock_agent_id
    lock_agent_id="$(python3 -c "import json; d=json.load(open('$path')); print(d['agent_id'])" 2>/dev/null || echo "")"
    if [[ "$lock_agent_id" != "$agent_id" ]]; then
        echo "FORBIDDEN: lock belongs to agent '$lock_agent_id', not '$agent_id'" >&2
        return 1
    fi

    rm -f "$path"
    echo "RELEASED: lock for '$feature' removed"
}

cmd_check() {
    local feature="${1:-}"
    if [[ -z "$feature" ]]; then
        echo "Usage: tools/agent-lock.sh check <feature>" >&2
        return 1
    fi
    local path
    path="$(_lock_path "$feature")"

    if [[ ! -f "$path" ]]; then
        echo "FREE: no lock for '$feature'"
        return 0
    fi

    local pid pid_started_at
    pid="$(python3 -c "import json; d=json.load(open('$path')); print(d['pid'])" 2>/dev/null || echo "0")"
    pid_started_at="$(python3 -c "import json; d=json.load(open('$path')); print(d.get('pid_started_at') or '')" 2>/dev/null || echo "")"
    if [[ "$pid" -gt 0 ]] && _is_stale "$pid" "$pid_started_at"; then
        rm -f "$path"
        echo "FREE: stale lock removed for '$feature'"
        return 0
    fi

    echo "LOCKED: '$feature'"
    python3 -c "
import json
d = json.load(open('$path'))
print(f\"  agent_id : {d['agent_id']}\")
print(f\"  branch   : {d['branch']}\")
print(f\"  worktree : {d.get('worktree', 'none')}\")
print(f\"  since    : {d['started_at']}\")
"
    return 1
}

cmd_check_branch() {
    # The unit of exclusion for pushes is the remote branch, not the feature
    # label — two sessions with different feature names can still collide on
    # one branch (observed 2026-07-16 on docs/public-launch-readiness).
    # Exit 0: FREE (no live lock for this branch) or OWNED (this session
    # holds it, via AGENTHARNESS_AGENT_ID match or ancestor-pid match).
    # Exit 1: LOCKED by another live session.
    local branch="${1:-}"
    if [[ -z "$branch" ]]; then
        echo "Usage: tools/agent-lock.sh check-branch <branch>" >&2
        return 1
    fi
    mkdir -p "$LOCKS_DIR"
    # Block if ANY live lock on this branch belongs to another session —
    # an owned lock must not mask a foreign one, so scan every lock file
    # before answering OWNED.
    local owned_feature=""
    local f
    for f in "$LOCKS_DIR"/*.json; do
        [[ -f "$f" ]] || continue
        local info
        # Path passed as argv, never interpolated into Python source; pid
        # coerced to int and multiline field values flattened so the
        # line-oriented read below can't be misaligned by crafted content.
        info="$(python3 - "$f" 2>/dev/null <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
def line(v):
    print(str(v if v is not None else '').replace('\n', ' ').replace('\r', ' '))
line(d.get('branch', ''))
line(d.get('agent_id', ''))
try:
    print(int(d.get('pid') or 0))
except (TypeError, ValueError):
    print(0)
line(d.get('feature', ''))
line(d.get('started_at', ''))
# Command substitution strips trailing newlines, so a genuinely empty
# last field would silently disappear from $info below and starve the
# final `read` — print a non-empty sentinel instead of an empty line.
pid_started_at = d.get('pid_started_at')
line(pid_started_at if pid_started_at is not None else 'NONE')
PYEOF
)" || continue
        local l_branch l_agent l_pid l_feature l_since l_pid_started_at
        {
            read -r l_branch
            read -r l_agent
            read -r l_pid
            read -r l_feature
            read -r l_since
            read -r l_pid_started_at
        } <<< "$info"
        [[ "$l_pid_started_at" == "NONE" ]] && l_pid_started_at=""
        [[ "$l_branch" == "$branch" ]] || continue
        if [[ "$l_pid" -gt 0 ]] && _is_stale "$l_pid" "$l_pid_started_at"; then
            rm -f "$f"
            continue
        fi
        if [[ -n "${AGENTHARNESS_AGENT_ID:-}" && "$l_agent" == "$AGENTHARNESS_AGENT_ID" ]]; then
            owned_feature="$l_feature"
            continue
        fi
        if [[ "$l_pid" -gt 0 ]] && _is_ancestor_pid "$l_pid"; then
            owned_feature="$l_feature"
            continue
        fi
        echo "LOCKED: branch '$branch' is held by another live agent session." >&2
        echo "  feature  : $l_feature" >&2
        echo "  agent_id : $l_agent" >&2
        echo "  since    : $l_since" >&2
        echo "Wait for it to release, or coordinate — see patterns/multi-agent-coordination/COORDINATION.md" >&2
        return 1
    done
    if [[ -n "$owned_feature" ]]; then
        echo "OWNED: branch '$branch' is locked by this session (feature '$owned_feature')."
        return 0
    fi
    echo "FREE: no live lock for branch '$branch'"
    return 0
}

cmd_list() {
    mkdir -p "$LOCKS_DIR"
    local count=0
    for f in "$LOCKS_DIR"/*.json; do
        [[ -f "$f" ]] || continue
        local pid pid_started_at
        pid="$(python3 -c "import json; d=json.load(open('$f')); print(d['pid'])" 2>/dev/null || echo "0")"
        pid_started_at="$(python3 -c "import json; d=json.load(open('$f')); print(d.get('pid_started_at') or '')" 2>/dev/null || echo "")"
        if [[ "$pid" -gt 0 ]] && _is_stale "$pid" "$pid_started_at"; then
            rm -f "$f"
            continue
        fi
        count=$((count + 1))
        python3 -c "
import json
d = json.load(open('$f'))
print(f\"  [{d['feature']}] branch={d['branch']} agent={d['agent_id'][:8]}...\")
"
    done
    if [[ $count -eq 0 ]]; then
        echo "No active locks."
    fi
}

cmd_clean() {
    mkdir -p "$LOCKS_DIR"
    local removed=0
    for f in "$LOCKS_DIR"/*.json; do
        [[ -f "$f" ]] || continue
        local pid pid_started_at
        pid="$(python3 -c "import json; d=json.load(open('$f')); print(d['pid'])" 2>/dev/null || echo "0")"
        pid_started_at="$(python3 -c "import json; d=json.load(open('$f')); print(d.get('pid_started_at') or '')" 2>/dev/null || echo "")"
        if [[ "$pid" -le 0 ]] || _is_stale "$pid" "$pid_started_at"; then
            rm -f "$f"
            removed=$((removed + 1))
        fi
    done
    echo "Cleaned $removed stale lock(s)."
}

cmd_suggest_branch() {
    local feature="${1:-}"
    if [[ -z "$feature" ]]; then
        echo "Usage: tools/agent-lock.sh suggest-branch <feature>" >&2
        return 1
    fi
    local slug
    slug="$(_slug "$feature" | cut -c1-20)"
    local ts
    ts="$(date +%s)"
    local rand
    rand="$(head -c 4 /dev/urandom | xxd -p | head -c 6 2>/dev/null || echo "000000")"
    echo "feat/${slug}-agent-${ts}-${rand}"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    command="${1:-}"
    shift || true
    case "$command" in
        acquire)        cmd_acquire "$@" ;;
        release)        cmd_release "$@" ;;
        check)          cmd_check "$@" ;;
        check-branch)   cmd_check_branch "$@" ;;
        list)           cmd_list ;;
        clean)          cmd_clean ;;
        suggest-branch) cmd_suggest_branch "$@" ;;
        *)
            echo "Usage:" >&2
            echo "  tools/agent-lock.sh acquire <feature> <branch> [worktree]" >&2
            echo "  tools/agent-lock.sh release <feature> [agent_id]  (defaults to \$AGENTHARNESS_AGENT_ID)" >&2
            echo "  tools/agent-lock.sh check   <feature>" >&2
            echo "  tools/agent-lock.sh check-branch <branch>" >&2
            echo "  tools/agent-lock.sh list" >&2
            echo "  tools/agent-lock.sh clean" >&2
            echo "  tools/agent-lock.sh suggest-branch <feature>" >&2
            echo "See patterns/multi-agent-coordination/COORDINATION.md" >&2
            exit 1 ;;
    esac
fi
