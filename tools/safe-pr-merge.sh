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
#   1. Verify PR's CI checks are green
#   2. Detect whether an automated reviewer is configured on this repo
#   3. If configured: poll for new review comments on THIS PR (up to 20 min)
#   4. Verify all review comments have replies
#   5. Merge the PR
#   6. Poll post-merge CI to terminal state and report conclusion

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

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
    url="$(git config --get remote.origin.url)"
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

    # Check if any of those PRs have an automated review check-run
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

    # Check issue-level comments for replies
    local issue_comments
    issue_comments="$(gh pr view "$pr_num" -R "$repo" --json comments -q '.comments[] | select(.authorAssociation!="OWNER") | .id' 2>/dev/null || true)"

    while IFS= read -r comment_id; do
        if [ -z "$comment_id" ]; then continue; fi
        # For issue-level comments, check if there's a reply in the PR
        # (simplified: count total comments as a proxy for replies)
        unanswered+=("issue-$comment_id")
    done < <(echo "$issue_comments")

    # Check inline review comments for replies
    local inline_comments
    inline_comments="$(gh api repos/"$repo"/pulls/"$pr_num"/comments --paginate -q '.[] | select(.in_reply_to_id == null) | .id' 2>/dev/null || true)"

    while IFS= read -r comment_id; do
        if [ -z "$comment_id" ]; then continue; fi
        unanswered+=("inline-$comment_id")
    done < <(echo "$inline_comments")

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
wait_for_ci_run() {
    local repo="$1"
    local branch="$2"

    log_step "Waiting for CI run on branch '$branch' to complete..."

    # Get the most recent run for this branch
    local run_id
    run_id="$(gh run list -R "$repo" -b "$branch" --limit 1 -q '.[0].databaseId' 2>/dev/null || echo "")"

    if [ -z "$run_id" ]; then
        log_info "No CI run found yet for branch '$branch'; waiting a moment..."
        sleep 5
        run_id="$(gh run list -R "$repo" -b "$branch" --limit 1 -q '.[0].databaseId' 2>/dev/null || echo "")"

        if [ -z "$run_id" ]; then
            log_error "Could not find CI run for branch '$branch'"
            return 1
        fi
    fi

    log_info "Polling CI run $run_id..."

    # Poll until terminal state
    local status="in_progress"
    local elapsed=0
    local max_wait=$((60 * 5))  # 5 minutes max wait

    while [ "$status" == "in_progress" ] || [ "$status" == "queued" ] || [ "$status" == "requested" ]; do
        if [ $elapsed -gt $max_wait ]; then
            log_error "CI run polling timeout (${max_wait}s)"
            return 1
        fi

        status="$(gh run view "$run_id" -R "$repo" -q '.status' 2>/dev/null || echo "unknown")"

        if [ "$status" != "in_progress" ] && [ "$status" != "queued" ] && [ "$status" != "requested" ]; then
            break
        fi

        log_info "CI run status: $status (elapsed ${elapsed}s)"
        sleep 10
        elapsed=$((elapsed + 10))
    done

    # Check conclusion
    local conclusion
    conclusion="$(gh run view "$run_id" -R "$repo" -q '.conclusion' 2>/dev/null || echo "unknown")"

    log_info "CI run completed with status: $status, conclusion: $conclusion"

    if [ "$conclusion" != "success" ]; then
        log_error "Post-merge CI failed (conclusion: $conclusion)"
        return 1
    fi

    log_info "Post-merge CI is green"
    return 0
}

# Main entrypoint
main() {
    if [ $# -lt 1 ]; then
        echo "Usage: $(basename "$0") <pr-number> [gh pr merge options]" >&2
        return 1
    fi

    local pr_num="$1"
    shift
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
        if ! poll_for_review_comments "$pr_num" "$repo" "$PR_REVIEW_WAIT_SECS"; then
            log_error "Timeout waiting for automated review comments"
            return 1
        fi

        # Step 4: Verify all comments have replies
        if ! verify_all_comments_replied "$pr_num" "$repo"; then
            log_error "Not all review comments have been addressed"
            return 1
        fi
    else
        log_info "No automated reviewer configured; skipping review-comment wait"
    fi

    # Get PR details (base branch, etc.)
    local base_branch
    base_branch="$(gh pr view "$pr_num" -R "$repo" -q '.baseRefName' 2>/dev/null || echo "")"

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

    # Step 6: Wait for post-merge CI
    if ! wait_for_ci_run "$repo" "$base_branch"; then
        log_error "Post-merge CI failed on branch '$base_branch'"
        return 1
    fi

    log_info "Safe merge of PR #$pr_num complete!"
    return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
