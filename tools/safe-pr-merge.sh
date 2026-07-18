#!/usr/bin/env bash
# safe-pr-merge.sh — merge a PR safely by enforcing the CLAUDE.md checklist.
#
# Bakes the PR-merge mandate from CLAUDE.md into a single script to prevent
# agents from skipping steps (e.g. waiting for review, checking comments,
# verifying post-merge CI). Refuses with a clear error message if any step fails.
#
# Usage:
#   bash tools/safe-pr-merge.sh <pr-number> [gh pr merge options]
#
# Examples:
#   bash tools/safe-pr-merge.sh 42
#   bash tools/safe-pr-merge.sh 42 --delete-branch
#
# Exit codes:
#   0 — PR merged successfully and post-merge CI is green
#   1 — any step failed (CI checks, review comments, merge, post-merge CI)
#
# Checklist (enforced in order):
#   0. Warn (not block) if this copy of the script differs from the one on
#      the repo's default branch — a stale checkout can silently reproduce
#      already-fixed bugs in this file itself (see issue #99)
#   1. Verify PR's CI checks are green
#   2. Detect whether an automated reviewer is configured on this repo
#   3. If configured: poll for new review comments on THIS PR (up to 20 min,
#      short-circuits immediately once the reviewer's check-run completes
#      with zero comments — a finished review satisfies the wait even if it
#      found nothing to say)
#   4. Verify all review comments have replies
#   5. Merge the PR
#   6. Poll post-merge CI to terminal state and report conclusion — matched
#      by the merge commit's SHA, not just "newest run on the branch"
#      (that alone races GitHub's run-list indexing; see issue #94)

set -euo pipefail

# Deliberately NO cd-to-script-root here: the tool operates on whatever
# repo the caller is standing in (same resolution as gh itself), so a
# consumer install can use it on the consumer's own PRs.

# Configuration
PR_REVIEW_WAIT_SECS=$((20 * 60))      # 20 minutes
POLL_INTERVAL_SECS=30

log_step() {
    echo "[STEP] $1" >&2
}

log_info() {
    echo "[INFO] $1" >&2
}

log_error() {
    echo "[ERROR] $1" >&2
}

# Get repo owner/name from git remote
get_repo_owner_name() {
    local url
    # || true: git config exits 1 when the key is unset, and under set -e
    # a failing assignment would kill the function before the error below
    # ever prints.
    url="$(git config --get remote.origin.url || true)"
    # Handle both https://github.com/owner/repo.git and git@github.com:owner/repo.git
    if [[ "$url" =~ github\.com[:/]([^/]+)/(.+?)(\.git)?$ ]]; then
        echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}" | sed 's/\.git$//'
    else
        log_error "Could not parse repo owner/name from remote URL: $url"
        return 1
    fi
}

# Check if PR's CI checks are all green
check_pr_ci() {
    local pr_num="$1"
    local repo="$2"

    log_step "Checking PR #$pr_num CI status..."

    # Get PR checks
    local checks
    checks="$(gh pr checks "$pr_num" -R "$repo" 2>/dev/null || true)"

    if [ -z "$checks" ]; then
        log_error "Could not fetch PR #$pr_num checks"
        return 1
    fi

    # Look for any FAIL or PENDING status
    if echo "$checks" | grep -E '(FAIL|PENDING)' >/dev/null 2>&1; then
        log_error "PR #$pr_num CI checks are not all green. Status:"
        echo "$checks" >&2
        return 1
    fi

    log_info "PR #$pr_num CI checks are green"
}

# Detect if an automated reviewer is configured on this repo
# by checking recent PRs for bot review check-runs
detect_automated_reviewer() {
    local repo="$1"

    log_step "Checking if automated reviewer is configured on this repo..."

    # Get the last 5 merged PRs (should be enough to detect if a reviewer is active)
    local pr_nums
    pr_nums="$(gh pr list -R "$repo" -S 'is:merged' --limit 5 --json number -q '.[].number' 2>/dev/null || true)"

    if [ -z "$pr_nums" ]; then
        log_info "No recent merged PRs found; assuming no automated reviewer is configured"
        return 1  # Not configured
    fi

    # Check if any of those PRs have an automated review check-run.
    # local is load-bearing: without it this loop variable clobbers the
    # caller's global pr_num with the last merged PR inspected, and every
    # later step then polls/merges the wrong PR (caught dogfooding the
    # script on its own PR #87 — it waited on #86's comments).
    local pr_num
    for pr_num in $pr_nums; do
        # Look for Copilot or other bot review checks
        if gh api repos/"$repo"/pulls/"$pr_num"/reviews -q '.[] | select(.user.login | test("bot|copilot|github-actions")) | .user.login' 2>/dev/null | grep -E '(bot|copilot|github-actions)' >/dev/null 2>&1; then
            log_info "Automated reviewer detected (found bot/Copilot reviews in recent PRs)"
            return 0  # Configured
        fi
    done

    log_info "No automated reviewer detected in recent PRs"
    return 1  # Not configured
}

# True if the automated reviewer's check-run for the PR's current head
# commit has reached a *completed* state (started-but-pending doesn't
# count — only a finished run means "the review already happened").
#
# Matches on check-run *name* against "copilot" or "code review"-shaped
# terms specifically, not "bot" or "github-actions" — every check-run on
# this repo's own CI runs under the "github-actions" app slug regardless
# of what job it is, and "bot" is a substring collision waiting to happen
# against unrelated job names (e.g. a future "robot-tests" job). A false
# match here would short-circuit the wait on a check-run that was never
# the reviewer at all.
review_check_run_completed() {
    local pr_num="$1"
    local repo="$2"

    local head_sha
    head_sha="$(gh pr view "$pr_num" -R "$repo" --json headRefOid -q '.headRefOid' 2>/dev/null || echo "")"
    if [ -z "$head_sha" ]; then
        return 1
    fi

    gh api repos/"$repo"/commits/"$head_sha"/check-runs \
        -q '.check_runs[] | select(.name | test("copilot|code.?review"; "i")) | select(.status == "completed") | .name' \
        2>/dev/null | grep -q .
}

# Poll for review comments on the PR (up to timeout)
poll_for_review_comments() {
    local pr_num="$1"
    local repo="$2"
    local wait_secs="$3"

    log_step "Waiting for review comments on PR #$pr_num (up to ${wait_secs}s)..."

    local elapsed=0
    local start_time
    start_time="$(date +%s)"

    while [ $elapsed -lt $wait_secs ]; do
        # Check both issue comments and inline review comments
        local issue_comments
        issue_comments="$(gh pr view "$pr_num" -R "$repo" --json comments -q '.comments | length' 2>/dev/null || echo 0)"

        local inline_comments
        inline_comments="$(gh api repos/"$repo"/pulls/"$pr_num"/comments -q 'length' 2>/dev/null || echo 0)"

        local total_comments=$((issue_comments + inline_comments))

        if [ "$total_comments" -gt 0 ]; then
            log_info "Found $total_comments review comments on PR #$pr_num"
            return 0  # Found comments
        fi

        # A completed review check-run IS the wait this step exists to
        # enforce — a started-but-still-running run is not (see CLAUDE.md's
        # PR-merge checklist exception). Sitting out the rest of a 20-minute
        # window after the reviewer has already finished and left nothing
        # to address only delays the merge for no benefit.
        if review_check_run_completed "$pr_num" "$repo"; then
            log_info "Automated review check-run already completed on PR #$pr_num with zero comments — review has already happened, no need to wait out the rest of the window"
            return 0  # Wait satisfied by a completed run; verify_all_comments_replied is a no-op with zero comments
        fi

        elapsed=$(($(date +%s) - start_time))
        if [ $elapsed -lt $wait_secs ]; then
            log_info "No review comments yet; waiting ${POLL_INTERVAL_SECS}s (elapsed ${elapsed}s / ${wait_secs}s)..."
            sleep $POLL_INTERVAL_SECS
        fi
    done

    log_info "Timeout waiting for review comments (${wait_secs}s elapsed)"
    return 1  # No comments found
}

# Verify all review comments have replies
verify_all_comments_replied() {
    local pr_num="$1"
    local repo="$2"

    log_step "Verifying all review comments have replies..."

    local unanswered=()
    local pr_author
    pr_author="$(gh pr view "$pr_num" -R "$repo" --json author -q '.author.login' 2>/dev/null || echo "")"

    # Issue-level comments have no threading; the mandate's reply
    # convention is a later `gh pr comment` from the PR author. A
    # non-author comment counts as answered if any author comment is
    # newer than it.
    local issue_unreplied
    issue_unreplied="$(gh pr view "$pr_num" -R "$repo" --json comments 2>/dev/null \
        | python3 -c '
import json, sys
author = sys.argv[1]
comments = json.load(sys.stdin).get("comments", [])
author_times = [c["createdAt"] for c in comments if c["author"]["login"] == author]
last_author = max(author_times) if author_times else ""
for c in comments:
    if c["author"]["login"] != author and c["createdAt"] > last_author:
        print(c["id"])
' "$pr_author" 2>/dev/null || true)"

    while IFS= read -r comment_id; do
        if [ -z "$comment_id" ]; then continue; fi
        unanswered+=("issue-$comment_id")
    done < <(echo "$issue_unreplied")

    # Inline review comments thread via in_reply_to_id: a top-level
    # comment is answered when any other comment replies to its id.
    local inline_unreplied
    inline_unreplied="$(gh api repos/"$repo"/pulls/"$pr_num"/comments --paginate 2>/dev/null \
        | python3 -c '
import json, sys
comments = json.load(sys.stdin)
replied_to = {c.get("in_reply_to_id") for c in comments if c.get("in_reply_to_id")}
for c in comments:
    if c.get("in_reply_to_id") is None and c["id"] not in replied_to:
        print(c["id"])
' 2>/dev/null || true)"

    while IFS= read -r comment_id; do
        if [ -z "$comment_id" ]; then continue; fi
        unanswered+=("inline-$comment_id")
    done < <(echo "$inline_unreplied")

    if [ ${#unanswered[@]} -gt 0 ]; then
        log_error "Found ${#unanswered[@]} unanswered comments:"
        for cid in "${unanswered[@]}"; do
            log_error "  - $cid"
        done
        return 1
    fi

    log_info "All review comments have been addressed"
    return 0
}

# Wait for a GitHub Actions run to complete
#
# expected_sha is the merge commit this run must belong to. "Most recent
# run for the branch" is not a safe proxy for "the run this merge
# triggered" — GitHub's run-list index can lag a few seconds behind a
# merge, so an immediate query can return the *previous* run instead of
# the new one. If that previous run happened to already be green, this
# function would report a false "post-merge CI is green" while the real
# run for this merge was still queued (observed live: PR #93's merge,
# see docs/operational/harness-feedback.md 2026-07-18 entry / issue #94).
# Retrying on headSha match, not just presence, closes that race.
wait_for_ci_run() {
    local repo="$1"
    local branch="$2"
    local expected_sha="$3"

    log_step "Waiting for CI run on branch '$branch' (commit ${expected_sha:0:12}) to complete..."

    # Find the run whose headSha matches the merge commit, not just
    # whatever happens to be newest in the list yet.
    local run_id=""
    local find_elapsed=0
    # Overridable so tests can exercise the timeout path in seconds, not
    # minutes; production callers get the real 120s default.
    local find_max_wait="${SAFE_PR_MERGE_FIND_RUN_MAX_WAIT:-120}"
    while [ -z "$run_id" ]; do
        run_id="$(gh run list -R "$repo" -b "$branch" -c "$expected_sha" --limit 1 --json databaseId \
            -q '.[0].databaseId // empty' 2>/dev/null || echo "")"

        if [ -n "$run_id" ]; then
            break
        fi

        if [ $find_elapsed -ge $find_max_wait ]; then
            log_error "No CI run found for commit ${expected_sha:0:12} on branch '$branch' after ${find_max_wait}s"
            return 1
        fi

        log_info "No CI run yet for commit ${expected_sha:0:12}; waiting 5s (elapsed ${find_elapsed}s / ${find_max_wait}s)..."
        sleep 5
        find_elapsed=$((find_elapsed + 5))
    done

    log_info "Polling CI run $run_id..."

    # Poll until terminal state
    local status="in_progress"
    local elapsed=0
    # This repo's full CI takes ~6-8 minutes wall time; 5 minutes would
    # time out on every healthy run.
    local max_wait=$((60 * 15))

    while [ "$status" == "in_progress" ] || [ "$status" == "queued" ] || [ "$status" == "requested" ]; do
        if [ $elapsed -gt $max_wait ]; then
            log_error "CI run polling timeout (${max_wait}s)"
            return 1
        fi

        status="$(gh run view "$run_id" -R "$repo" --json status -q '.status' 2>/dev/null || echo "unknown")"

        if [ "$status" != "in_progress" ] && [ "$status" != "queued" ] && [ "$status" != "requested" ]; then
            break
        fi

        log_info "CI run status: $status (elapsed ${elapsed}s)"
        sleep 10
        elapsed=$((elapsed + 10))
    done

    # Check conclusion
    local conclusion
    conclusion="$(gh run view "$run_id" -R "$repo" --json conclusion -q '.conclusion' 2>/dev/null || echo "unknown")"

    log_info "CI run completed with status: $status, conclusion: $conclusion"

    if [ "$conclusion" != "success" ]; then
        log_error "Post-merge CI failed (conclusion: $conclusion)"
        return 1
    fi

    log_info "Post-merge CI is green"
    return 0
}

# Warn (never block — this repo's own sessions routinely need to run
# in-progress edits to this exact script) if the running copy differs
# from the version on the repo's default branch. Issue #99: merging PR
# #95 from a branch forked before PR #96 landed silently reran the
# pre-#96 script and reproduced the false-green bug #96 had just fixed,
# with no signal from the tool itself that it was stale. Compared by
# blob hash (git hash-object) rather than diffing text, so it's
# insensitive to how the file happens to be read.
warn_if_stale_script() {
    local default_branch
    default_branch="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')" || true
    default_branch="${default_branch:-main}"

    git fetch --quiet origin "$default_branch" 2>/dev/null || return 0

    local rel_path
    rel_path="$(git ls-files --full-name -- "${BASH_SOURCE[0]}" 2>/dev/null | head -1)"
    [ -z "$rel_path" ] && return 0

    local upstream_hash current_hash
    upstream_hash="$(git rev-parse "origin/$default_branch:$rel_path" 2>/dev/null || echo "")"
    [ -z "$upstream_hash" ] && return 0
    current_hash="$(git hash-object "${BASH_SOURCE[0]}" 2>/dev/null || echo "")"
    [ -z "$current_hash" ] && return 0

    if [ "$upstream_hash" != "$current_hash" ]; then
        log_error "WARNING: this copy of $rel_path differs from origin/$default_branch's version."
        log_error "  A stale or locally-modified copy of this script can silently reproduce"
        log_error "  already-fixed bugs (see issue #99). If this isn't a deliberate test of a"
        log_error "  local change, switch to $default_branch (or 'git checkout $default_branch --"
        log_error "  $rel_path') before merging."
    fi
}

# Main entrypoint
main() {
    if [ $# -lt 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        echo "Usage: $(basename "$0") <pr-number> [gh pr merge options]" >&2
        return 1
    fi

    warn_if_stale_script

    local pr_num="$1"
    shift

    # Everything downstream feeds pr_num into gh; a non-numeric value
    # (e.g. --help) makes gh print usage text to stdout, which then gets
    # misread as check results or comment counts.
    if ! [[ "$pr_num" =~ ^[0-9]+$ ]]; then
        echo "Usage: $(basename "$0") <pr-number> [gh pr merge options]" >&2
        log_error "PR number must be numeric, got: $pr_num"
        return 1
    fi
    local merge_args=("$@")

    # Get repo owner/name
    local repo
    repo="$(get_repo_owner_name)" || return 1

    log_info "Merging PR #$pr_num in repo $repo"

    # Step 1: Check CI
    check_pr_ci "$pr_num" "$repo" || return 1

    # Step 2: Detect automated reviewer
    local reviewer_configured=0
    if detect_automated_reviewer "$repo"; then
        reviewer_configured=1
    fi

    # Step 3: If configured, wait for review comments
    if [ "$reviewer_configured" -eq 1 ]; then
        if poll_for_review_comments "$pr_num" "$repo" "$PR_REVIEW_WAIT_SECS"; then
            # Step 4: Verify all comments have replies
            if ! verify_all_comments_replied "$pr_num" "$repo"; then
                log_error "Not all review comments have been addressed"
                return 1
            fi
        else
            # The mandate requires the *wait*, not that comments exist —
            # a full window with no review is a valid outcome to merge on.
            log_info "Review-wait window elapsed with no comments; proceeding"
        fi
    else
        log_info "No automated reviewer configured; skipping review-comment wait"
    fi

    # Get PR details (base branch, etc.)
    local base_branch
    base_branch="$(gh pr view "$pr_num" -R "$repo" --json baseRefName -q '.baseRefName' 2>/dev/null || echo "")"

    if [ -z "$base_branch" ]; then
        log_error "Could not determine PR base branch"
        return 1
    fi

    log_info "PR base branch: $base_branch"

    # Step 5: Merge the PR
    log_step "Merging PR #$pr_num..."
    if ! gh pr merge "$pr_num" -R "$repo" --merge "${merge_args[@]}"; then
        log_error "Failed to merge PR #$pr_num"
        return 1
    fi

    log_info "PR #$pr_num merged successfully"

    # Get the merge commit SHA so Step 6 can verify it's polling the run
    # this merge actually triggered, not just whatever's newest on the
    # branch (see wait_for_ci_run's comment for why that distinction
    # matters).
    local merge_sha=""
    local sha_elapsed=0
    while [ -z "$merge_sha" ] && [ $sha_elapsed -lt 30 ]; do
        merge_sha="$(gh pr view "$pr_num" -R "$repo" --json mergeCommit -q '.mergeCommit.oid // empty' 2>/dev/null || echo "")"
        if [ -z "$merge_sha" ]; then
            sleep 3
            sha_elapsed=$((sha_elapsed + 3))
        fi
    done

    if [ -z "$merge_sha" ]; then
        log_error "Could not determine merge commit SHA for PR #$pr_num"
        return 1
    fi

    log_info "Merge commit: $merge_sha"

    # Step 6: Wait for post-merge CI
    if ! wait_for_ci_run "$repo" "$base_branch" "$merge_sha"; then
        log_error "Post-merge CI failed on branch '$base_branch'"
        return 1
    fi

    log_info "Safe merge of PR #$pr_num complete!"
    return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
