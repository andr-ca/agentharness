#!/usr/bin/env bats
# Tests for tools/agent-lock.sh

setup() {
    # Create a temp dir as the project root with locks dir
    TEST_ROOT="$(mktemp -d)"
    mkdir -p "$TEST_ROOT/.agentharness-locks"
    # Make agent-lock.sh use TEST_ROOT as the project root
    export TEST_ROOT
    export AGENTHARNESS_ROOT="$TEST_ROOT"
    # Use the test's own PID as AGENT_LOCK_PID so locks appear alive
    export AGENT_LOCK_PID="$$"
}

teardown() {
    rm -rf "$TEST_ROOT"
}

LOCK_SCRIPT="$BATS_TEST_DIRNAME/../../tools/agent-lock.sh"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_acquire() {
    local feature="$1"
    local branch="${2:-feat/test}"
    # Run with project root override via subshell env
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "$feature" "$branch" 2>&1) | tail -1
}

_check() {
    local feature="$1"
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" check "$feature" 2>&1) | head -1
}

_release() {
    local feature="$1"
    local agent_id="$2"
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" release "$feature" "$agent_id" 2>&1) | head -1
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@test "acquire: creates a lock file" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "my-feature" "feat/my-feature")
    local slug
    slug="$(echo "my-feature" | tr '[:upper:]' '[:lower:]' | tr ' /' '-')"
    # Check that at least one .json file was created
    local count
    count="$(find "$TEST_ROOT/.agentharness-locks" -name '*.json' | wc -l)"
    [[ $count -ge 1 ]]
}

@test "acquire: returns an agent_id" {
    local id
    id="$(_acquire "my-feature")"
    # UUID-shaped output: 36 chars with dashes
    [[ ${#id} -ge 30 ]]
}

@test "check: FREE when no lock" {
    local result
    result="$(_check "no-such-feature")"
    [[ "$result" == *"FREE"* ]]
}

@test "check: LOCKED after acquire" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "locked-feature" "feat/locked")
    local result
    result="$(_check "locked-feature")"
    [[ "$result" == *"LOCKED"* ]]
}

@test "release: removes lock when agent_id matches" {
    local agent_id
    agent_id="$(_acquire "releaseable-feature")"
    local result
    result="$(_release "releaseable-feature" "$agent_id")"
    [[ "$result" == *"RELEASED"* ]]
    local check_result
    check_result="$(_check "releaseable-feature")"
    [[ "$check_result" == *"FREE"* ]]
}

@test "release: fails when agent_id does not match" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "mine" "feat/mine")
    local result
    result="$(_release "mine" "wrong-agent-id")"
    [[ "$result" == *"FORBIDDEN"* ]] || [[ "$result" == *"NOT FOUND"* ]]
}

@test "release: missing agent_id prints usage instead of crashing on unbound variable" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "usage-release" "feat/usage-release")
    local rc=0
    local result
    # Explicitly unset so this stays deterministic even if the bats
    # process itself inherited AGENTHARNESS_AGENT_ID from its caller —
    # otherwise the release fallback (tested separately below) would
    # mask the missing-arg path this test exists to cover.
    result="$(cd "$TEST_ROOT" && unset AGENTHARNESS_AGENT_ID; bash "$LOCK_SCRIPT" release "usage-release" 2>&1)" || rc=$?
    [[ $rc -ne 0 ]]
    [[ "$result" == *"Usage: tools/agent-lock.sh release <feature> <agent_id>"* ]]
}

@test "release: missing feature prints usage instead of crashing on unbound variable" {
    local rc=0
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" release 2>&1)" || rc=$?
    [[ $rc -ne 0 ]]
    [[ "$result" == *"Usage: tools/agent-lock.sh release"* ]]
}

@test "release: falls back to AGENTHARNESS_AGENT_ID env var when agent_id omitted" {
    local agent_id
    agent_id="$(_acquire "env-fallback-feature")"
    local result
    result="$(cd "$TEST_ROOT" && AGENTHARNESS_AGENT_ID="$agent_id" bash "$LOCK_SCRIPT" release "env-fallback-feature" 2>&1)"
    [[ "$result" == *"RELEASED"* ]]
}

@test "acquire: missing branch prints usage instead of crashing on unbound variable" {
    local rc=0
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "only-feature" 2>&1)" || rc=$?
    [[ $rc -ne 0 ]]
    [[ "$result" == *"Usage: tools/agent-lock.sh acquire <feature> <branch> [worktree]"* ]]
}

@test "check: missing feature prints usage instead of crashing on unbound variable" {
    local rc=0
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" check 2>&1)" || rc=$?
    [[ $rc -ne 0 ]]
    [[ "$result" == *"Usage: tools/agent-lock.sh check <feature>"* ]]
}

@test "check-branch: missing branch prints usage instead of crashing on unbound variable" {
    local rc=0
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" check-branch 2>&1)" || rc=$?
    [[ $rc -ne 0 ]]
    [[ "$result" == *"Usage: tools/agent-lock.sh check-branch <branch>"* ]]
}

@test "suggest-branch: missing feature prints usage instead of crashing on unbound variable" {
    local rc=0
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" suggest-branch 2>&1)" || rc=$?
    [[ $rc -ne 0 ]]
    [[ "$result" == *"Usage: tools/agent-lock.sh suggest-branch <feature>"* ]]
}

@test "acquire: blocked when active lock exists" {
    local first_id
    first_id="$(_acquire "contested" "feat/contested")"
    local rc=0
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "contested" "feat/other") || rc=$?
    [[ $rc -ne 0 ]]
}

@test "suggest-branch: returns a branch name" {
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" suggest-branch "my-feature" 2>&1)"
    [[ "$result" == feat/* ]]
}

@test "list: shows no locks when none exist" {
    local result
    result="$(cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" list 2>&1)"
    [[ "$result" == *"No active locks"* ]]
}

@test "clean: removes stale locks" {
    # Write a lock with a non-existent PID (99999999)
    cat > "$TEST_ROOT/.agentharness-locks/stale-abc12345.json" << 'EOF'
{
  "agent_id": "stale-agent",
  "feature": "stale-feature",
  "branch": "feat/stale",
  "worktree": null,
  "started_at": "2000-01-01T00:00:00Z",
  "pid": 99999999
}
EOF
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" clean)
    local count
    count="$(find "$TEST_ROOT/.agentharness-locks" -name 'stale-*.json' | wc -l)"
    [[ $count -eq 0 ]]
}

# ---------------------------------------------------------------------------
# pid reuse (#148): kill -0 alone can't tell a still-running owner from an
# unrelated process that has since reused the recorded pid number. Every
# lock written by 'acquire' now also records the pid's own process-start
# time (pid_started_at); staleness checks compare it against that pid's
# CURRENT start time, not just whether the pid answers kill -0.
# ---------------------------------------------------------------------------

@test "acquire: records pid_started_at for the recorded pid" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "pid-start-feature" "feat/pid-start")
    local f
    f="$(find "$TEST_ROOT/.agentharness-locks" -name '*.json' | head -1)"
    run python3 -c "import json; d=json.load(open('$f')); print(d['pid_started_at'])"
    [ "$status" -eq 0 ]
    # ps -o lstart= parsing is best-effort (Copilot review): an epoch is the
    # expected case on a real bats process, but a platform where it's
    # undeterminable correctly records JSON null (printed as "None" here) —
    # both are valid outcomes, not just the numeric one.
    [[ "$output" =~ ^[0-9]+$ || "$output" == "None" ]]
}

_write_lock_with_pid_started_at() {
    # A lock recorded as owned by $$ (alive throughout this test, matching
    # the file's AGENT_LOCK_PID=$$ convention) but with a caller-supplied
    # pid_started_at, so tests can simulate either a correct match (still
    # the real owner) or a mismatch (pid reused by someone else). Written
    # to the exact slugged path `check` expects (matching _lock_path), not
    # a hand-picked filename — `check` looks up that exact path directly,
    # unlike check-branch/list/clean, which glob every *.json in the dir.
    local name="$1" branch="$2" pid_started_at="$3"
    local path
    path="$( (source "$LOCK_SCRIPT"; _lock_path "$name") )"
    cat > "$path" <<JSON
{
  "agent_id": "reuse-test-agent",
  "feature": "$name",
  "branch": "$branch",
  "worktree": null,
  "started_at": "2026-01-01T00:00:00Z",
  "pid": $$,
  "pid_started_at": $pid_started_at
}
JSON
}

@test "pid reuse: a lock whose pid_started_at doesn't match the live pid's actual start is treated as stale, not alive" {
    # $$ is genuinely alive (this bats process), so a bare kill -0 check
    # would call this lock live indefinitely — exactly the #148 failure
    # mode (a merged, week-old lock read as "live" because kill -0 happened
    # to match an unrelated process that later reused the recorded pid).
    _write_lock_with_pid_started_at "reused-pid" "feat/reused" "1"
    run bash "$LOCK_SCRIPT" check "reused-pid"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
    [ ! -f "$TEST_ROOT/.agentharness-locks/reused-pid.json" ]
}

@test "pid reuse: clean removes a lock whose pid_started_at doesn't match, even though the pid answers kill -0" {
    _write_lock_with_pid_started_at "reused-pid-clean" "feat/reused-clean" "1"
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" clean)
    [ ! -f "$TEST_ROOT/.agentharness-locks/reused-pid-clean.json" ]
}

@test "pid reuse: check-branch treats a pid_started_at mismatch as stale and reports the branch FREE" {
    _write_lock_with_pid_started_at "reused-pid-branch" "feat/reused-branch" "1"
    run bash "$LOCK_SCRIPT" check-branch "feat/reused-branch"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
}

@test "pid reuse: no false positive — a live pid whose pid_started_at genuinely matches is not treated as stale" {
    local real_started_at
    real_started_at="$(python3 -c "
import subprocess
out = subprocess.run(['ps', '-o', 'lstart=', '-p', '$$'], capture_output=True, text=True).stdout
from datetime import datetime
raw = ' '.join(out.split())
print(int(datetime.strptime(raw, '%a %b %d %H:%M:%S %Y').timestamp()))
")"
    _write_lock_with_pid_started_at "same-pid" "feat/same" "$real_started_at"
    run bash "$LOCK_SCRIPT" check "same-pid"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

@test "pid reuse: backward compat — a lock with no pid_started_at field falls back to kill-0-only (pre-#148 lock files)" {
    local path
    path="$( (source "$LOCK_SCRIPT"; _lock_path "old-format") )"
    cat > "$path" <<JSON
{
  "agent_id": "old-format-agent",
  "feature": "old-format",
  "branch": "feat/old-format",
  "worktree": null,
  "started_at": "2026-01-01T00:00:00Z",
  "pid": $$
}
JSON
    run bash "$LOCK_SCRIPT" check "old-format"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

# ---------------------------------------------------------------------------
# check-branch (branch is the unit of exclusion for pushes)
# ---------------------------------------------------------------------------

_write_foreign_lock() {
    # A lock held by a live process that is NOT an ancestor of this test.
    local branch="$1"
    local pid="$2"
    cat > "$TEST_ROOT/.agentharness-locks/foreign-feature-deadbeef.json" <<JSON
{
  "agent_id": "11111111-2222-3333-4444-555555555555",
  "branch": "$branch",
  "feature": "foreign-feature",
  "pid": $pid,
  "started_at": "2026-07-16T00:00:00Z",
  "worktree": null
}
JSON
}

@test "check-branch: FREE when no locks exist" {
    run bash "$LOCK_SCRIPT" check-branch "feat/anything"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
}

@test "check-branch: blocks when another live session holds the branch" {
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/contested" "$other_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/contested"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
    [[ "$output" =~ "foreign-feature" ]]
}

@test "check-branch: a lock on a different branch does not block" {
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/other-branch" "$other_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/mine"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
}

@test "check-branch: OWNED via AGENTHARNESS_AGENT_ID match" {
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/contested" "$other_pid"
    run env AGENTHARNESS_AGENT_ID="11111111-2222-3333-4444-555555555555" \
        bash "$LOCK_SCRIPT" check-branch "feat/contested"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OWNED" ]]
}

@test "check-branch: OWNED via ancestor pid without env var" {
    # AGENT_LOCK_PID=$$ (the bats process) is an ancestor of the check
    # subshell, so a lock this test acquires is recognized as its own.
    _acquire "my-own-feature" "feat/my-own"
    run bash "$LOCK_SCRIPT" check-branch "feat/my-own"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OWNED" ]]
}

@test "check-branch: stale lock (dead pid) is removed and branch is FREE" {
    # A guaranteed-nonexistent pid (above the kernel's pid_max) instead of
    # a reaped process's pid, which could be recycled on a busy host.
    local dead_pid=$(( $(cat /proc/sys/kernel/pid_max 2>/dev/null || echo 4194304) + 1 ))
    _write_foreign_lock "feat/contested" "$dead_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/contested"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
    [ ! -f "$TEST_ROOT/.agentharness-locks/foreign-feature-deadbeef.json" ]
}

@test "check-branch: owned lock does not mask a foreign live lock on the same branch" {
    _acquire "my-own-feature" "feat/shared"
    sleep 60 &
    local other_pid=$!
    _write_foreign_lock "feat/shared" "$other_pid"
    run bash "$LOCK_SCRIPT" check-branch "feat/shared"
    kill "$other_pid" 2>/dev/null || true
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

# ---------------------------------------------------------------------------
# Lease liveness (#148): pid liveness alone cannot represent a logical agent
# session. Clients that run each tool call in a fresh process (and even
# long-lived shells, when acquire runs inside a command substitution) leave a
# recorded pid that dies immediately while the session continues. Every lock
# now carries an explicit `lease_expires_at`; a lock is stale only when its
# pid is dead-or-reused AND its lease has expired, so a dead pid can no
# longer silently expire a live session's lock.
# ---------------------------------------------------------------------------

_dead_pid() {
    # Above the kernel's pid_max, so it can never belong to a live process.
    echo $(( $(cat /proc/sys/kernel/pid_max 2>/dev/null || echo 4194304) + 1 ))
}

_write_lease_lock() {
    # A lock owned by an agent_id, with caller-chosen pid and lease offset in
    # seconds relative to now (negative = already expired).
    local name="$1" branch="$2" pid="$3" lease_offset="$4" agent_id="${5:-lease-test-agent}"
    local path
    path="$( (source "$LOCK_SCRIPT"; _lock_path "$name") )"
    local lease
    lease="$(python3 -c "
import sys
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) + timedelta(seconds=int(sys.argv[1]))).strftime('%Y-%m-%dT%H:%M:%SZ'))
" "$lease_offset")"
    cat > "$path" <<JSON
{
  "agent_id": "$agent_id",
  "feature": "$name",
  "branch": "$branch",
  "worktree": null,
  "started_at": "2026-01-01T00:00:00Z",
  "pid": $pid,
  "pid_started_at": null,
  "lease_expires_at": "$lease"
}
JSON
}

@test "lease: acquire records a lease_expires_at in the future" {
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" acquire "lease-feature" "feat/lease")
    local f
    f="$(find "$TEST_ROOT/.agentharness-locks" -name '*.json' | head -1)"
    run python3 -c "
import json
from datetime import datetime, timezone
d = json.load(open('$f'))
lease = datetime.strptime(d['lease_expires_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
print('FUTURE' if lease > datetime.now(timezone.utc) else 'PAST')
"
    [ "$status" -eq 0 ]
    [[ "$output" == "FUTURE" ]]
}

@test "lease: acquiring process exits but the lease keeps the lock alive (the #148 primary report)" {
    # The exact stateless-client shape: the process that ran acquire is gone,
    # the logical session continues. Before the lease, this read as stale and
    # the lock silently vanished.
    _write_lease_lock "stateless-feature" "feat/stateless" "$(_dead_pid)" 3600
    run bash "$LOCK_SCRIPT" check "stateless-feature"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

@test "lease: the owner still passes check-branch after its acquiring process exited" {
    _write_lease_lock "stateless-feature" "feat/stateless" "$(_dead_pid)" 3600 "my-session-id"
    AGENTHARNESS_AGENT_ID="my-session-id" run bash "$LOCK_SCRIPT" check-branch "feat/stateless"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OWNED" ]]
}

@test "lease: the owner can still release after its acquiring process exited" {
    _write_lease_lock "stateless-feature" "feat/stateless" "$(_dead_pid)" 3600 "my-session-id"
    run bash "$LOCK_SCRIPT" release "stateless-feature" "my-session-id"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "RELEASED" ]]
}

@test "lease: a foreign session is still blocked while the lease is valid" {
    _write_lease_lock "stateless-feature" "feat/stateless" "$(_dead_pid)" 3600 "someone-elses-id"
    AGENTHARNESS_AGENT_ID="my-different-id" run bash "$LOCK_SCRIPT" check-branch "feat/stateless"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

@test "lease: a crashed owner is recoverable once the lease expires" {
    _write_lease_lock "crashed-feature" "feat/crashed" "$(_dead_pid)" -60
    run bash "$LOCK_SCRIPT" check "crashed-feature"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "FREE" ]]
}

@test "lease: clean removes a dead-pid lock only after its lease has expired" {
    _write_lease_lock "still-leased" "feat/a" "$(_dead_pid)" 3600
    _write_lease_lock "lease-done" "feat/b" "$(_dead_pid)" -60
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" clean)
    [ -f "$( (source "$LOCK_SCRIPT"; _lock_path "still-leased") )" ]
    [ ! -f "$( (source "$LOCK_SCRIPT"; _lock_path "lease-done") )" ]
}

@test "lease: a live pid keeps the lock alive even after the lease expires" {
    # A genuinely long-lived shell must not lose its lock just because the
    # TTL elapsed — pid liveness and lease validity are independent grants.
    _write_lease_lock "longlived-feature" "feat/longlived" "$$" -60
    run bash "$LOCK_SCRIPT" check "longlived-feature"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

@test "lease: backward compat — a lock with no lease_expires_at keeps pid-only semantics" {
    cat > "$TEST_ROOT/.agentharness-locks/legacy-abc12345.json" <<JSON
{
  "agent_id": "legacy-agent",
  "feature": "legacy-feature",
  "branch": "feat/legacy",
  "worktree": null,
  "started_at": "2000-01-01T00:00:00Z",
  "pid": $(_dead_pid)
}
JSON
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" clean)
    [ ! -f "$TEST_ROOT/.agentharness-locks/legacy-abc12345.json" ]
}

@test "lease: list agrees with check — a dead-pid lock under a valid lease is still listed" {
    _write_lease_lock "listed-feature" "feat/listed" "$(_dead_pid)" 3600
    run bash "$LOCK_SCRIPT" list
    [ "$status" -eq 0 ]
    [[ "$output" =~ "listed-feature" ]]
}

@test "renew: the owner extends its own lease" {
    _write_lease_lock "renew-feature" "feat/renew" "$(_dead_pid)" 60 "my-session-id"
    local path
    path="$( (source "$LOCK_SCRIPT"; _lock_path "renew-feature") )"
    local before
    before="$(python3 -c "import json; print(json.load(open('$path'))['lease_expires_at'])")"
    run bash "$LOCK_SCRIPT" renew "renew-feature" "my-session-id"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "RENEWED" ]]
    local after
    after="$(python3 -c "import json; print(json.load(open('$path'))['lease_expires_at'])")"
    [[ "$after" > "$before" ]]
}

@test "renew: a foreign agent_id cannot extend someone else's lease" {
    _write_lease_lock "renew-feature" "feat/renew" "$(_dead_pid)" 60 "owner-id"
    run bash "$LOCK_SCRIPT" renew "renew-feature" "not-the-owner"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "FORBIDDEN" ]]
}

@test "renew: falls back to AGENTHARNESS_AGENT_ID like release does" {
    _write_lease_lock "renew-feature" "feat/renew" "$(_dead_pid)" 60 "env-session-id"
    AGENTHARNESS_AGENT_ID="env-session-id" run bash "$LOCK_SCRIPT" renew "renew-feature"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "RENEWED" ]]
}

@test "renew: missing feature prints usage instead of crashing on unbound variable" {
    run bash "$LOCK_SCRIPT" renew
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Usage" ]]
}

# ---------------------------------------------------------------------------
# Session marker (#148): a PreToolUse/pre-push hook runs in its own process
# and does NOT inherit an AGENTHARNESS_AGENT_ID exported inline by the agent's
# own shell, so env-var ownership proof is unavailable exactly where the push
# gate needs it. acquire therefore also records the id in a per-checkout
# session marker that any process standing in the checkout can read.
# ---------------------------------------------------------------------------

@test "session marker: check-branch reports OWNED with no env var and no ancestor pid" {
    _write_lease_lock "marker-feature" "feat/marker" "$(_dead_pid)" 3600 "marker-session-id"
    echo "marker-session-id" >> "$TEST_ROOT/.agentharness-locks/.session-ids"
    run env -u AGENTHARNESS_AGENT_ID bash "$LOCK_SCRIPT" check-branch "feat/marker"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "OWNED" ]]
}

@test "session marker: acquire records the agent_id in the marker file" {
    local id
    id="$(_acquire "marker-write" "feat/marker-write")"
    grep -q "$id" "$TEST_ROOT/.agentharness-locks/.session-ids"
}

@test "session marker: release drops the id so a released lock stops proving ownership" {
    local id
    id="$(_acquire "marker-drop" "feat/marker-drop")"
    (cd "$TEST_ROOT" && bash "$LOCK_SCRIPT" release "marker-drop" "$id")
    run grep -q "$id" "$TEST_ROOT/.agentharness-locks/.session-ids"
    [ "$status" -ne 0 ]
}

@test "session marker: an id not in this checkout's marker does not prove ownership" {
    _write_lease_lock "marker-feature" "feat/marker" "$(_dead_pid)" 3600 "someone-elses-id"
    echo "my-own-unrelated-id" >> "$TEST_ROOT/.agentharness-locks/.session-ids"
    run env -u AGENTHARNESS_AGENT_ID bash "$LOCK_SCRIPT" check-branch "feat/marker"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOCKED" ]]
}

# ---------------------------------------------------------------------------
# AGENT_LOCK_LEASE_SECONDS validation. A documented override makes a typo a
# realistic input, and an unvalidated one used to reach Python's int() inside
# the mutex critical section: the ValueError killed the script under `set -e`,
# the EXIT trap then died on an already-unwound local, and the mutex directory
# leaked — permanently failing every later acquire of that feature with
# "RACE: could not acquire mutex".
# ---------------------------------------------------------------------------

@test "lease override: a non-integer value is rejected with a clear message" {
    run env AGENT_LOCK_LEASE_SECONDS=abc bash "$LOCK_SCRIPT" acquire "bad-lease" "feat/bad-lease"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "AGENT_LOCK_LEASE_SECONDS" ]]
    [[ ! "$output" =~ "Traceback" ]]
}

@test "lease override: zero is rejected (a lock born already expired is not useful)" {
    run env AGENT_LOCK_LEASE_SECONDS=0 bash "$LOCK_SCRIPT" acquire "zero-lease" "feat/zero-lease"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "AGENT_LOCK_LEASE_SECONDS" ]]
}

@test "lease override: a rejected value leaves no lock and no leaked mutex directory" {
    run env AGENT_LOCK_LEASE_SECONDS=abc bash "$LOCK_SCRIPT" acquire "bad-lease" "feat/bad-lease"
    [ "$status" -eq 1 ]
    [[ "$(find "$TEST_ROOT/.agentharness-locks" -name '*.json' | wc -l)" -eq 0 ]]
    [[ "$(find "$TEST_ROOT/.agentharness-locks" -maxdepth 1 -type d -name '.mutex-*' | wc -l)" -eq 0 ]]
}

@test "lease override: the feature is still acquirable after a rejected attempt" {
    # The regression that mattered most: a leaked mutex used to deadlock the
    # feature permanently, needing a manual rmdir to recover.
    run env AGENT_LOCK_LEASE_SECONDS=abc bash "$LOCK_SCRIPT" acquire "bad-lease" "feat/bad-lease"
    [ "$status" -eq 1 ]
    run bash "$LOCK_SCRIPT" acquire "bad-lease" "feat/bad-lease"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ACQUIRED" ]]
}

@test "lease override: a valid value is honoured" {
    run env AGENT_LOCK_LEASE_SECONDS=60 bash "$LOCK_SCRIPT" acquire "good-lease" "feat/good-lease"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ACQUIRED" ]]
}

@test "lease override: renew rejects a bad value too" {
    _write_lease_lock "renew-bad" "feat/renew-bad" "$(_dead_pid)" 60 "owner-id"
    run env AGENT_LOCK_LEASE_SECONDS=abc bash "$LOCK_SCRIPT" renew "renew-bad" "owner-id"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "AGENT_LOCK_LEASE_SECONDS" ]]
}

# ---------------------------------------------------------------------------
# acquire's success output must expose the recorded owner pid. A wrong
# AGENT_LOCK_PID (e.g. pointing at an unrelated process that happens to be a
# long-lived agent client) otherwise reports success identically to a correct
# one, and the mistake only surfaces later as a push blocked by the agent's
# OWN lock — with an error naming the very agent_id the caller holds.
# ---------------------------------------------------------------------------

@test "acquire: reports the recorded owner pid, not just the agent_id" {
    run env AGENT_LOCK_PID=$$ bash "$LOCK_SCRIPT" acquire "pid-visible" "feat/pid-visible"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "owner_pid=$$" ]]
}

@test "acquire: notes when the owner pid is unrelated to the acquiring process" {
    # A live pid that is not an ancestor: ownership will not be recognized by
    # hook processes via the ancestor check, so say so at acquire time.
    sleep 60 &
    local stranger=$!
    run env AGENT_LOCK_PID="$stranger" bash "$LOCK_SCRIPT" acquire "pid-stranger" "feat/pid-stranger"
    kill "$stranger" 2>/dev/null || true
    [ "$status" -eq 0 ]
    [[ "$output" =~ "NOTE" ]]
    [[ "$output" =~ "not an ancestor" ]]
}

@test "acquire: stays quiet when the owner pid is a genuine ancestor" {
    run env AGENT_LOCK_PID=$$ bash "$LOCK_SCRIPT" acquire "pid-ancestor" "feat/pid-ancestor"
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "not an ancestor" ]]
}
