---
date: 2026-07-17
topic: operational
purpose: Dated log of harness friction found while using agentharness itself, per the harness-feedback skill
---

# Harness Feedback Log

Friction found while *using* this harness, recorded per
`.claude/skills/harness-feedback/SKILL.md`: what happened → root cause →
impact → what agentharness should change → corrective action taken. In
consuming projects this file lives at the same path; entries here are the
self-hosted (dogfood) case.

## 2026-07-30 – a PreToolUse hook cannot be live-verified in the session that adds it

**Recurrence key:** `hook-not-active-until-next-session`

**Harness version:** 7a1deb6

**What happened:** After adding `.github/hooks/claude-pr-merge-guard.sh` and wiring
it into `.claude/settings.json`, I live-tested it the obvious way — ran
`gh pr merge 999999`, expecting the guard to block the tool call. It did not.
The command ran and reached GitHub (failing only because the PR does not exist).

**Root cause:** Claude Code loads `PreToolUse` hooks at session start. A hook
added part-way through a session is on disk and correctly wired, but not
registered with the running session, so it cannot fire until the next one. The
observable result — "my new guard did not block anything" — is indistinguishable
from "my new guard is broken".

**Impact:** the misleading signal points the wrong way, and the natural responses
are both bad. An agent may waste time debugging a hook that is already correct,
or "fix" a working guard until it does something visible. Worse, an agent that
concludes the guard does not work may skip wiring it at all, or disable it — so
a correct safety control gets removed because of a session-lifecycle artifact.
The repo's own mandate to live-verify externally-triggered behaviour actively
pushes toward this test, which is what makes the trap likely rather than
incidental.

**What agentharness should change:** say so where hooks are documented — a
`PreToolUse` hook is not testable in the session that introduces it, and the
substitute is to pipe the exact tool payload through the script directly plus
read back the `.claude/settings.json` wiring. That is a complete verification of
the hook's logic and its registration; only the session-lifecycle step remains,
and it closes on the next session's first matching tool call. Worth stating in
the harness-feedback and live-verification guidance so the disclosure is
recognised as sufficient rather than treated as a skipped check.

**Corrective action taken:** verified by piping the exact payload Claude Code
sends for `gh pr merge 999999` through the hook (blocked, exit 2) and the
`safe-pr-merge.sh` form (allowed, exit 0), and by reading back the settings
wiring. Disclosed the limitation explicitly in PR #207 rather than implying
end-to-end confirmation, and recorded that first real firing will be the next
session's first merge attempt. Not filed as a separate upstream issue for the
reason recorded in the `safe-pr-merge-arg-passthrough` entry: this is the
upstream repo and the finding is recorded here.

## 2026-07-29 – completion gate reports success with a required file left untracked

**Recurrence key:** `completion-gate-untracked-blindspot`

**Harness version:** e05944c

**What happened:** Added a new skill (`.claude/skills/project-bootstrap/`) and
its `.agents/skills/` symlink. `tools/check-completion.sh` returned
`can_declare_complete: true` with the symlink still untracked. The defect was
caught much later by the pre-push bats suite —
`generate-agents-md: path resolution — every referenced .agents/skills/*/SKILL.md
path exists on disk` — after a full push cycle had already been spent.

**Root cause:** the gate's `git-clean` check reports "N uncommitted change(s) to
tracked files". A brand-new file that was never `git add`-ed is not a tracked
file, so it is invisible to the check. Every other gate (lint, types, tests,
coverage) operates on the working tree, where the file is present and
everything passes — so the whole gate goes green on a state that cannot be
reproduced from the commit.

**Impact:** the gate's entire purpose is to be the last word before declaring
work done, and this is the one class of mistake it structurally cannot see:
new files. It is also the most likely mistake when adding a skill, a test
fixture, or a generated artifact — exactly the work the gate is most often run
after. The failure surfaces later and far from its cause.

**What agentharness should change:** `git-clean` should count untracked,
non-ignored files as uncommitted too — `git status --porcelain
--untracked-files=all` already reports both in one call. Anything genuinely
transient belongs in `.gitignore`, which the check would then correctly skip.

**Corrective action taken:** Created the missing symlink and committed it.
Logged here; the gate change itself is a separate scoped fix, not folded into
this feature branch.

## 2026-07-28 – `safe-pr-merge.sh` reports a false CI failure on a transient status read

**Recurrence key:** `safe-pr-merge-ci-status-misread`

**Harness version:** ba4f484

**What happened:** `safe-pr-merge.sh 185` merged the PR, then reported
`Post-merge CI failed (conclusion: )` and exited 1. The post-merge run for that
exact merge commit had in fact completed successfully. The log showed
`CI run completed with status: unknown, conclusion:` at 120s elapsed — against a
900s polling budget, so nothing had timed out.

**Root cause:** the status poll fell back to the literal string `unknown` when
`gh run view` failed (`... || echo "unknown"`). `unknown` is not
`in_progress`/`queued`/`requested`, so the loop treated it as a terminal state
and broke out, then read the conclusion of a still-running job — which is empty
— and the `[ "$conclusion" != "success" ]` test turned that empty value into
"CI failed". A single transient API error was therefore enough to manufacture a
failure report for a healthy run.

**Impact:** the inverse of the earlier false-green defects logged against this
same tool, and arguably worse for trust: an agent that believes post-merge CI
failed will start investigating or reverting work that is actually fine, and an
operator who learns the failure reports are unreliable will discount the real
ones. The tool exists specifically to make "merged" and "CI passed" separate,
trustworthy claims.

**What agentharness should change:** distinguish "could not read the status"
from "the run reached a terminal state" — retry a failed read, bounded so a
persistently broken `gh` still terminates. Separately, an empty or unreadable
conclusion should be reported as unknown rather than as a failure; conflating
them trains the reader to distrust genuine failures.

**Corrective action taken:** Verified against the actual run before believing
the report (`gh run list --branch main`) — the merge commit's run was
`completed/success`. Fixed in the PR carrying this entry: failed status reads
are retried up to 3 consecutive times, an empty/unknown conclusion is reported
as undetermined with an explicit "this is unknown, NOT a failure" message, and
the misleading "CI run completed with status: unknown" wording is gone. Not
filed as a separate upstream issue for the same reason recorded in the
`safe-pr-merge-arg-passthrough` entry: this is the upstream repo and the fix
landed in the same session.

## 2026-07-28 – `safe-pr-merge.sh` documents "[gh pr merge options]" but hardcodes `--merge`

**Recurrence key:** `safe-pr-merge-arg-passthrough`

**Harness version:** 74672e6

**What happened:** Ran `bash tools/safe-pr-merge.sh 172 --squash --delete-branch`
to merge a green Dependabot PR. The script spent its full ~20-minute
automated-reviewer poll, then failed at the merge step with gh's usage error
"only one of --merge, --rebase, or --squash can be enabled". The PR was not
merged, and the whole wait had to be repeated.

**Root cause:** The script's usage line advertises
`safe-pr-merge.sh <pr-number> [gh pr merge options]`, but line 455 invokes
`gh pr merge "$pr_num" -R "$repo" --merge "${merge_args[@]}"` — the merge
strategy is hardcoded, so any caller-supplied strategy flag collides with it.
The documented interface promises pass-through of options the implementation
cannot actually accept. `--delete-branch` works; `--squash`/`--rebase` cannot.

**Impact:** A ~20-minute wait wasted before the failure surfaced, because the
argument collision is only detected at the last step, after all the polling.
Compounded by a second-order trap: the failure is easy to miss when the script
is piped (e.g. `| tail -30`), because the pipe masks its non-zero exit status
and the run looks successful.

**What agentharness should change:** Either (a) detect a caller-supplied
strategy flag in `merge_args` and omit the hardcoded `--merge`, or (b) correct
the usage text to state that the strategy is fixed and only non-strategy
options pass through. (a) is preferable — the checklist this script enforces is
orthogonal to which merge strategy a repo wants. Validating conflicting
arguments up front, before the 20-minute poll rather than after it, is worth
doing either way.

**Corrective action taken:** Re-ran without the strategy flag and captured the
exit code instead of piping it. Fixed directly in PR #180 (merged), which
implemented option (a) plus up-front rejection of conflicting strategy flags,
and also fixed a second defect found in the same function: the reply check
anchored on the PR author, and GitHub reports a Dependabot PR's author as
`app/dependabot` while that bot's comments come from `dependabot`, so every
comment read as unanswered and replying added another. No separate upstream
issue was filed: this is the upstream repo, and the fix landed in the same
session the friction was found, so an issue would have been opened and closed
without ever carrying information the PR doesn't. Recorded here rather than
silently skipped.

## 2026-07-28 – `PreToolUse` push guard cannot see an inline-exported `AGENTHARNESS_AGENT_ID`

**Recurrence key:** `agent-lock-liveness`

**Harness version:** 74672e6

**What happened:** Holding a valid lock for the branch being pushed, ran
`export AGENTHARNESS_AGENT_ID=<id>; git push -u origin <branch>`. The
`claude-push-lock-guard.sh` `PreToolUse` hook blocked the push with "LOCKED:
branch is held by another live agent session" — and printed an `agent_id`
identical to the one being exported.

**Root cause:** Two compounding causes. The hook runs in its own process and
does not inherit an `AGENTHARNESS_AGENT_ID` exported inline within an agent
tool call, so `cmd_check_branch`'s env-var ownership proof is unavailable
exactly where the push gate needs it. The ancestor-pid fallback then also
failed, because the lock had been acquired with an `AGENT_LOCK_PID` pointing at
the wrong one of several `claude` processes on the host — an operator error the
tool gave no way to notice, since `acquire` reports success either way.

**Impact:** An agent can be blocked from pushing its own locked branch with an
error message that appears to contradict itself (the id it demands is the id it
prints). The natural workaround — `AGENTHARNESS_LOCK_BYPASS=1` — defeats the
mutex entirely, which is the wrong reflex to train.

**What agentharness should change:** Provide an ownership proof that does not
depend on env inheritance (a per-checkout session marker written at acquire
time). Separately, `acquire` should make the recorded owner pid visible in its
success output so a wrong `AGENT_LOCK_PID` is noticeable at acquire time rather
than at push time.

**Corrective action taken:** Diagnosed by running `check-branch` with and
without the env var to confirm the hook's actual view, then re-acquired with the
correct session pid. The session-marker proof is implemented in PR #174 against
issue #148, whose root cause this shares.

## 2026-07-17 – content-quality scan descends into `.claude/worktrees/`, false-failing the completion gate

**What happened:** Running `tools/check-completion.sh` before a commit on
PR #82, the content-quality gate failed with 12 mandate-restatement errors,
all inside `.claude/worktrees/agent-*/docs/operational/reviews/` — stale
checkouts left by finished subagent sessions, not current repo content.
The change under test was clean and CI was green throughout.

**Root cause:** Same failure class as launch-readiness item E9: that fix
pruned `.worktrees/` from the markdown scan in
`tools/verify-content-quality.py`, but Claude Code's agent worktrees live
under `.claude/worktrees/`, which the prune didn't cover.

**Impact:** The Stop-hook completion gate blocks on false failures whenever
a finished subagent worktree lingers; a commit was pushed with the gate red
(CI authoritative for this class), which is a bad pattern to normalize.

**What agentharness should change:** Exclude any `worktrees` path component
and `node_modules` from the markdown scan (the launch-plan addendum already
flagged nested `.kilo/node_modules`/`.opencode/node_modules`).

**Corrective action taken:** Removed the three stale agent worktrees
(`git worktree remove`), turning the gate green immediately; extended the
scanner exclusion in the same PR as this entry. Logged upstream as
[#83](https://github.com/andr-ca/agentharness/issues/83).

## 2026-07-18 – `safe-pr-merge.sh`'s post-merge CI wait can report a false green

**What happened:** Merging PR #93 with
`tools/safe-pr-merge.sh 93 --delete-branch`, the script's final step
reported "Post-merge CI is green" and "Safe merge complete" — but the run it polled
(`29645328747`) was a stale, already-`success` run left over from the
PR #91 merge ~50 minutes earlier, not the run PR #93's merge commit
(`8abf99a`) actually triggered (`29646923757`, still `queued` at that
moment).

**Root cause:** `wait_for_ci_run()` fetches "most recent run for
branch `main`" immediately after merging via `gh run list --limit 1`.
GitHub's run-list index can lag a few seconds behind the merge, so the
query can return the *previous* run instead of the new one. The
function never verifies the polled run's `headSha` matches the merge
commit, so a stale-but-green run silently satisfies the check.

**Impact:** The script exists specifically to enforce this repo's own
"never report a push/merge as done while CI is still running or red"
mandate, and in the race window it violates that mandate itself. No
bad state landed on `main` this time (the real run also passed), but
the script would have reported "complete" identically had the real run
failed.

**What agentharness should change:** `wait_for_ci_run` should take the
merge commit's SHA and verify the fetched run's `headSha` matches
before trusting it, retrying the lookup with backoff until a run for
that exact SHA appears.

**Corrective action taken:** Manually verified the real post-merge run
(`gh run watch 29646923757 --exit-status`) before reporting PR #93 as
done, so no false-green reached the user this session. Logged upstream
as [#94](https://github.com/andr-ca/agentharness/issues/94).

## 2026-07-18 – `safe-pr-merge.sh` reproduced the just-fixed false-green bug by running a stale copy of itself

**What happened:** Immediately after #94/#96 (above) merged, merging
PR #95 from a local checkout still on branch
`docs/harness-feedback-ci-race-94` — forked from `main` *before* #96
landed — ran that branch's pre-fix copy of `tools/safe-pr-merge.sh`. It
reported "Post-merge CI is green" for run `29650734547`, whose
`headSha` (`98b7e124`) did not match PR #95's actual merge commit
(`db75a6e2`); the real run (`29651378346`) was still `in_progress` at
that moment.

**Root cause:** the script's correctness depends entirely on which
version happens to be checked out in the caller's shell — it has no
self-check against `origin/main`, so a long-lived branch that forked
before a fix lands silently regresses the exact bug that fix closed.

**Impact:** a normal, correct workflow (working on a branch that forked
before a fix merged, then running the merge helper from that same
shell without an explicit `git checkout main` first) reintroduces a
just-fixed correctness bug with no warning from the tool itself.

**What agentharness should change:** `safe-pr-merge.sh` should warn (or
refuse) when invoked from a non-`main` branch, and/or compare its own
content against `origin/main`'s copy before trusting its own output.

**Corrective action taken:** Manually diffed the reported run's
`headSha` against `gh pr view --json mergeCommit` before trusting the
script's "complete" output, then watched the real run to a genuine
green. Logged upstream as
[#99](https://github.com/andr-ca/agentharness/issues/99).

## 2026-07-20 – Completion gate has no requirement to live-verify practically-testable automation before calling it done

**What happened:** Building the automated issue-analysis feature
(#107) across four PRs (#111, #113, #116, #118), the same pattern
repeated three times in a row: build a change to a GitHub-Actions-
triggered workflow, pass `tools/check-completion.sh` (lint/types/
tests/coverage all check out — none of it can exercise "does this
actually fire on a real webhook event"), write "Not live-tested —
[justification]" as an honest checklist item in the PR body, merge,
and stop there. The user had to explicitly ask "did you test it?"
(after #111) and "did you try testing it again?" (after #113's fix)
before actual live verification happened.

**Root cause:** `CLAUDE.md`'s Agent Workflow Completion mandate and the
completion gate are thorough about code-level verification (lint,
types, tests, coverage) and about process-level verification for the
merge itself (CI green, review addressed, post-merge CI confirmed
against the actual merge SHA) — the exact same "verified, not just
claimed" philosophy already applied rigorously to CI status. Neither
extends that philosophy to "does the feature I just built actually
work when triggered for real," for anything the local pytest/bats
suite structurally cannot exercise (webhook-triggered CI workflows,
cron jobs, external-service-dependent behavior). An agent can honestly
disclose "not live-tested" and still pass every gate, every time,
indefinitely.

**Impact:** Every time the user pushed for it, live-testing found a
real bug static checks completely missed: a duplicate-run race from
two webhook events firing for one issue (found by filing one throwaway
test issue), an indefinite hang in a third-party action only visible
by watching a live run for over an hour, and (without the nudge) a
plausible fourth repeat of the same pattern on the retry-mechanism PR.

**What agentharness should change:** Add an explicit item near the
Completion Gate: when a change adds or modifies something that only
truly runs via an external trigger the local suite can't simulate, the
agent must either exercise it for real before presenting the work as
done, or explicitly flag *why* live verification isn't happening this
round — framed as an open TODO the agent is expected to close out
proactively, not a satisfied requirement, mirroring the existing
"pushed ≠ verified green" distinction already drawn for CI status.

**Corrective action taken:** Live-tested all three workflow changes
after the fact (filed throwaway test issues, watched real runs,
force-verified the retry mechanism by racing a label removal mid-run)
once asked. Logged upstream as
[#121](https://github.com/andr-ca/agentharness/issues/121).

## 2026-07-20 – No guardrail against an agent writing to user dotfiles outside the repo

**What happened:** While acquiring a multi-agent lock, needed
`AGENTHARNESS_AGENT_ID` set for subsequent commands in the same shell.
Instead of exporting it inline for the current shell, ran a command
that appended it directly to the user's `~/.bashrc` — a file entirely
outside the repository, shared across every terminal session the user
opens. Caught immediately in the next tool result and reverted the
same turn, so no lasting harm.

**Root cause:** `CLAUDE.md`'s File Placement Policy
(`.agentharness-guarded-paths.json`, ask-before-creating-root-files) is
entirely scoped to files *inside the project working directory* — it
has no concept of "outside the repo entirely." A user's actual
home-directory dotfiles are, structurally, less protected than a new
file in the repo's own root would be.

**Impact:** No lasting harm this time, but nothing in the harness would
have stopped it if it hadn't been noticed immediately — no hook, no
guideline, no reflexive habit was in place for this class of action.

**What agentharness should change:** Add an explicit rule: never write
to files outside the current project's working directory tree without
explicit user confirmation — shell rc files, global git config, global
tool config directories, anything outside
`$(git rev-parse --show-toplevel)`. Session-scoped environment
variables should be exported inline for the current shell only, never
persisted to a dotfile, unless the user explicitly asks for a durable
environment change.

**Corrective action taken:** Detected the stray `.bashrc` line via the
system's file-change notification and removed it in the same turn
before it could affect a future session. Logged upstream as
[#122](https://github.com/andr-ca/agentharness/issues/122).

## 2026-07-22 – Hypothesis deadlines make the clean completion gate flaky under coverage

**What happened:** A clean worktree at `origin/main` (`fd0079e`) failed
`bash tools/check-completion.sh` before and after a documentation-only
change. The pytest-coverage gate showed five failures. A direct fail-fast
rerun exposed `hypothesis.errors.DeadlineExceeded`: a semantic profile
property test took 205.35 ms against Hypothesis's default 200 ms deadline.
The same test passed when run alone.

**Root cause:** The five profile property tests inherited Hypothesis's
environment-sensitive default per-example deadline even though they assert
semantic invariants, not performance budgets. Full-suite coverage
instrumentation and ordinary host load can push an example just over the
deadline.

**Impact:** The mandatory completion gate can fail on an unchanged clean
checkout, block unrelated documentation work, and encourage retry-until-green
behavior instead of deterministic verification. The gate's 20-line diagnostic
rerun also initially hid the root-cause line.

**What agentharness should change:** Disable Hypothesis deadlines explicitly
for these semantic property tests while preserving their generated examples
and assertions. Keep performance expectations in dedicated benchmarks or
explicit time-budget tests. Consider improving failure-output selection as a
separate change.

**Corrective action taken:** Added explicit `settings(deadline=None)` to all
five profile property tests and retained the existing assertions and example
counts. Logged upstream as
[#144](https://github.com/andr-ca/agentharness/issues/144).

## 2026-07-22 – Pre-push misclassifies agentharness worktrees as consumers

**What happened:** Pushing the verified
`docs/harness-engineering-roadmap-recommendations` branch from its linked
worktree caused the shared pre-push hook to report that the push was not to
agentharness and skip the repository's test suite. The pushed worktree and the
primary checkout are two worktrees of the same repository.

**Root cause:** The hook compared the hook-owning primary checkout's top-level
path with `git rev-parse --show-toplevel` from the pushed worktree. Linked
worktrees necessarily have different top-level paths even though they share
the same Git common directory. The hook also retained the primary checkout as
its execution root, which would test the wrong branch if only the path guard
were relaxed.

**Impact:** Agentharness pushes made through the repository's recommended
worktree workflow silently skipped both test/coverage enforcement and the
branch-lock gate. The output incorrectly described the worktree as an external
consumer. This push remained safe because the complete gate had already been
run manually.

**What agentharness should change:** Compare canonical Git common-directory
identity so linked worktrees are recognized as the same repository, retain the
no-op for unrelated consumers, and run checks from the pushed worktree rather
than the hook-owning checkout.

**Corrective action taken:** Updated the hook to compare common Git directories
and select the pushed worktree as its execution root. Added a Bats regression
using a real linked worktree while retaining the consumer no-op case. Logged
upstream as [#145](https://github.com/andr-ca/agentharness/issues/145).

## 2026-07-22 – Agent lock expires between stateless CLI tool calls

**What happened:** The feature lock acquired for
`harness-engineering-roadmap-recommendations` was gone when the session tried
to release it. `agent-lock.sh release` returned `NOT FOUND`, and
`agent-lock.sh list` reported no active locks even though the logical agent
session had remained active throughout the work.

**Root cause:** `agent-lock.sh acquire` records the acquisition shell's parent
PID by default. A client that runs each tool call in a separate process does
not have one long-lived shell parent, so that PID can exit while the logical
session continues. The cleanup paths treat PID death as authoritative;
`check-branch` removes a stale-PID lock before considering a matching exported
`AGENTHARNESS_AGENT_ID`.

**Impact:** Another agent can see the feature and branch as unlocked and begin
overlapping work while the original session is active. The documented session
identity does not preserve ownership for stateless command runners.

**What agentharness should change:** Define lock liveness for both long-lived
shells and stateless clients, likely through a renewable lease/heartbeat, an
explicit stable owner process, or session-token expiry semantics. Apply one
consistent rule to `check`, `check-branch`, `list`, and `clean`, with tests for
an exited acquisition process, the continuing owner, foreign sessions, and
abandoned-lock recovery.

**Corrective action taken:** Filed the design/correctness gap upstream as
[#148](https://github.com/andr-ca/agentharness/issues/148). Reacquired the lock
with an explicit stable PID for the short remainder of this session; no
concurrent work was observed. A production fix was deferred because changing
stale-owner semantics requires an explicit lease and recovery contract.

## 2026-07-23 – Fast-forward `git merge` into trunk bypasses `prevent-trunk-commit`

**What happened:** While dogfooding a local governed-action eval (a real
`opencode` agent asked to "integrate branch X into main" in a repo installed
with `harness-link.sh init --with-hook`), the agent fast-forward-merged the
feature branch onto trunk **3/3 times with hooks active**, and the trunk-commit
guard never fired. Reproduced by hand: direct `git commit` on trunk is blocked,
`git merge --no-ff` into trunk is blocked, but `git merge` that **fast-forwards**
trunk is not.

**Root cause:** `prevent-trunk-commit` is wired to `pre-commit` and
`pre-merge-commit`. A fast-forward merge moves the branch ref **without creating
a commit**, so neither hook runs — there is no commit or merge-commit event to
fire on.

**Impact:** The most ordinary integration command (`git merge <branch>` from an
up-to-date trunk) silently defeats trunk protection — the feature lands on trunk
with no PR, no review, no hook. This is the exact outcome the guard exists to
prevent, and an agent hit it naturally without trying to evade anything.

**What agentharness should change:** Add a `reference-transaction` hook (fires on
*all* ref updates, including fast-forwards) reusing `prevent-trunk-commit`'s
branch-matching; and/or write `merge.ff = false` into the installed git config so
a plain merge into trunk always creates a blockable merge commit; and document
that local hooks are best-effort and remote branch protection is the
authoritative guard. Distinct from #149 (hook not *shipped* via npm) — this
reproduces with the hook fully installed.

**Corrective action taken:** Verified the gap independently (not just inferred
from the eval), recorded it in the eval observations
(`eval-harness-observations-2026-07-23.md`, Finding 5b). Logged upstream as
[#155](https://github.com/andr-ca/agentharness/issues/155). Then validated a
minimal fix in a throwaway repo — `git config merge.ff false` forces a
blockable merge commit that the existing `pre-merge-commit` hook already
catches (no new hook needed; normal branch commits unaffected; documented
tradeoff = repo-wide merge commits when updating a branch from trunk). Posted
the validation + recommendation to
[#155](https://github.com/andr-ca/agentharness/issues/155#issuecomment-5067598904).

## 2026-07-24 – Stale agent-lock outlived its session by 7 days via PID reuse

**What happened:** While resuming work, `bash tools/agent-lock.sh list`
showed `launch-readiness-doc-corrections` as held (`agent=d8149edd...`,
`started_at: 2026-07-17T13:58:14Z`) — but the branch it locked
(`fix/launch-readiness-doc-corrections`) had merged via PR #85 on
2026-07-17, with no local branch, no remote branch, and no worktree left.
`bash tools/agent-lock.sh clean` reported "Cleaned 0 stale lock(s)."

**Root cause:** `_is_stale()` is `kill -0 "$pid"` and nothing else. The
lock's recorded `pid: 1468862` was, 7 days later, an unrelated VS Code
integrated-terminal bash shell (confirmed via `/proc/<pid>/cmdline` and
`/proc/<pid>/environ` — no `AGENTHARNESS_AGENT_ID`, unrelated command
line, started before the lock itself). `kill -0` succeeded on the reused
PID, so every command that trusts `_is_stale()` (`list`, `check-branch`,
`clean`) read a 7-day-dead lock as live.

**Impact:** No command in the tool could clear it — `clean` no-ops on a
"live" PID, and `release` correctly refuses without the original
`agent_id`, which no current session had. A merged, abandoned lock would
have sat there indefinitely, and worse, could make `check-branch` wrongly
report a genuinely free branch as owned by another session.

**What agentharness should change:** Same root cause as #148 (locks
expiring too early for stateless clients) — `_is_stale()` treating raw
PID liveness as authoritative is wrong in both directions. Recorded as a
second symptom on that issue rather than a new one, since the same
session-token/lease fix (not inferred solely from PID) closes both.

**Corrective action taken:** Independently verified the lock was dead
(branch merged, no local/remote branch, no worktree, PID's cmdline/environ
unrelated) before manually removing the lock file — the tool has no safe
command for this today. Logged upstream as a corroborating comment on
[#148](https://github.com/andr-ca/agentharness/issues/148#issuecomment-5073204356).

## 2026-07-25 – Third-party sandbox failure blocks the feedback procedure itself

**What happened:** During a local article-review task, the first read-only
repository command completed normally. Every subsequent shell command,
including `pwd` and `sed`, failed before the requested program started with
`bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. The failure
reproduced through both the direct command executor and its JavaScript
orchestration wrapper, with login-shell and TTY variations.

**Root cause:** The immediate failure was in the third-party Codex sandbox's
network-namespace setup, not in an agentharness script. The harness-feedback
skill nevertheless triggers broadly on tool-output friction and mandates an
upstream agentharness issue even when agentharness does not own the failing
runtime. Its procedure also assumes local shell access remains available to
inspect the opt-out flag, append this log, and run `gh issue create`.

**Impact:** The gitignored local `media/` article could not be read, so the
requested scored review and companion Markdown file could not be produced
until the workspace sandbox was restored. The same outage prevented local
skill reads, opt-out inspection, ordinary repository writes, the completion
gate, staging, and commits.

**What agentharness should change:** Limit mandatory upstream feedback to
harness-owned rules, hooks, scripts, generated configuration, and documented
integrations. Add a degraded-mode procedure for third-party runtime failures:
allow read-only API fallbacks, prohibit guessing local opt-out state, and
explain how to report a blocked local log or completion gate without treating
that blockage as another agentharness defect.

**Corrective action taken:** After the workspace sandbox was restored, read
the local skills and opt-out state, resumed the article review, and recorded
the complete incident. Logged upstream as
[#162](https://github.com/andr-ca/agentharness/issues/162).

## 2026-07-25 – `agent-lock.sh release` crashes when `agent_id` is omitted

**What happened:** Releasing locks at the end of a session (the work that
became PR #165), `bash tools/agent-lock.sh release "<feature>"` aborted with
`tools/agent-lock.sh: line 222: $2: unbound variable`. `cmd_release()` reads
`local agent_id="$2"` under `set -u`, so a missing second argument produces a
raw bash diagnostic naming an internal line number instead of a usage message.
The usage banner does not recover it: it lists subcommand *names* followed by
a bare `...`, documenting no arguments for any subcommand.

**Root cause:** Asymmetric signatures with no validation. `acquire` takes
`<feature> <branch>`; `release` takes `<feature> <agent_id>` — a different
second argument, of a different kind, which the caller must have retained
from the acquire output potentially hours earlier. Symmetry makes
`release "<feature>" "<branch>"` the natural guess and `release "<feature>"`
the second guess; neither is validated.

**Impact:** Low in this instance — `agent-lock.sh list` confirmed both locks
were already released, so nothing was left stale. The latent risk is the
timing: release runs at session end, when an agent is winding down and least
likely to stop and read the source to work out what `$2` was. An agent that
shrugs at an opaque crash leaves a stale lock behind, which is precisely the
failure the coordination protocol exists to prevent.

**What agentharness should change:** Validate arguments explicitly in
`cmd_release` (and audit sibling subcommands for the same pattern), printing
`Usage: agent-lock.sh release <feature> <agent_id>` and a hint that the id is
the value `acquire` printed and the protocol already mandates exporting as
`AGENTHARNESS_AGENT_ID`. Better still, default `agent_id` to that environment
variable when the argument is absent — it is almost always set, and would
have made this invocation succeed. Expand the usage banner to per-subcommand
argument lists.

**Corrective action taken:** Verified no stale locks remained. Logged
upstream as
[#166](https://github.com/andr-ca/agentharness/issues/166). This entry was
deliberately held until [#163](https://github.com/andr-ca/agentharness/pull/163)
merged, since that PR was open against this same file and appending
concurrently would have created an avoidable conflict.

## 2026-07-28 – First-run bootstrap is designed and partially built but has no usable surface

**Recurrence key:** `bootstrap-first-run-surface-integration`

**Harness version:** `65c1f39`

**What happened:** A user asked whether agentharness has a bootstrap skill
that assesses a repository on first use and helps tailor the harness to that
project. The installed skill inventory has no such skill. The stable
`harness-link.sh init` flow installs selected assets and generates guarded-path
configuration, but it does not perform the requested interactive capability
assessment. Meanwhile, the experimental Python CLI's `status` result directs
users to run `agentharness bootstrap`, although its argument parser does not
register a `bootstrap` command. `ROADMAP.md` also still describes PR #47 as in
progress even though GitHub records it as merged on 2026-07-16.

**Root cause:** PR #47 merged the project-bootstrap policy core and its design
artifacts without completing or consistently labeling the user-facing
integration. The stable installer, experimental core, CLI remediation, skill
inventory, manifest, and roadmap therefore describe different stages of the
same capability.

**Impact:** A first-time adopter cannot tell whether repository assessment is
available through a skill, the stable lifecycle installer, or the experimental
CLI. Following the CLI's own remediation fails with an invalid-command error,
while the stale roadmap obscures that the core merged but remains unreleased.

**What agentharness should change:** Establish one supported first-run
surface. Prefer a deterministic `agentharness bootstrap` command for discovery
and planning, paired with a thin `project-bootstrap` skill for interactive
questions and recommendation assessment. Until that ships, remove or qualify
the unavailable-command remediation, update the roadmap to distinguish the
merged core from the unreleased workflow, and test that every emitted
remediation command is registered.

**Corrective action taken:** Distinguished the stable installer from the
unreleased policy core, documented the current workaround as
`harness-link.sh plan/init` plus conversational assessment, and logged upstream
as [#187](https://github.com/andr-ca/agentharness/issues/187).

**Resolved 2026-07-29** by [#189](https://github.com/andr-ca/agentharness/pull/189):
`agentharness bootstrap plan|apply` and the `project-bootstrap` skill now ship,
so the workaround above is no longer the answer. Recorded rather than edited
away — this entry is what the repository actually looked like on 2026-07-28,
and the gap it describes is why the surface got built. Note the fix also had to
cover something this entry could not see: the npm launcher forwarded every
argument to `harness-link.sh` and never reached the Python core at all, so the
command would have been unreachable from an install even once it existed. Not
yet on npm — published is 0.3.0, and this needs a `v0.4.0` tag.

## 2026-07-28 – Agent locks are isolated between linked worktrees

**Recurrence key:** `agent-lock-worktree-shared-state`

**Harness version:** `f8941a8`

**What happened:** A feature lock was acquired from the primary checkout with
an isolated linked worktree recorded in the lock. After the work completed,
running `agent-lock.sh release` from that linked worktree returned `NOT FOUND`.
Running `check` from the primary checkout immediately afterward showed the
lock still live, and releasing it there succeeded.

**Root cause:** `agent-lock.sh` derives `REPO_ROOT` from the script's current
checkout path and stores records under `$REPO_ROOT/.agentharness-locks`.
Linked worktrees have distinct top-level paths and therefore distinct lock
directories. The `worktree` argument accepted by `acquire` is recorded only as
metadata; it does not select a repository-wide store.

**Impact:** Sessions working in different linked worktrees cannot see one
another's feature locks. `check-branch` and the pre-push hook can therefore
pass in one worktree while another live session holds the relevant lock in a
different checkout, defeating the coordination protocol precisely in its
recommended parallel-work setup.

**What agentharness should change:** Derive one canonical lock store from the
Git common directory or another repository-wide identity, while handling
existing root-level lock records deliberately. Add real linked-worktree tests
for cross-worktree acquire, check, renew, release, cleanup, and pre-push branch
enforcement. Until that ships, tell agents to run all lock commands from one
canonical checkout.

**Corrective action taken:** Located and released the live record from the
primary checkout where it was acquired, verified that store reported the
feature free, and logged upstream as
[#190](https://github.com/andr-ca/agentharness/issues/190).

---

## 2026-08-02 — outside-repo write guard blocks the agent's own memory store

**What happened:** Writing a memory file to
`~/.claude/projects/<project>/memory/<fact>.md` — the store Claude Code
tells a session to write to directly — was refused by
`.github/hooks/claude-outside-repo-write-guard.sh`:

> Blocked: … resolves outside any git repository and outside the system
> temp directory (/tmp).

**Why it matters:** the guard was doing exactly what it was written to do —
that path is outside every repository. But the effect is that installing
this harness silently disables the consuming agent's memory. Nothing
announces it: the write fails, the session continues, and every later
session starts without the notes it should have had. A guard that
degrades an unrelated capability without saying so is worse than one that
refuses loudly, because the cost lands on sessions that never see the
error.

It is also a scope error rather than a policy question. The guard's stated
purpose is protecting the *user's* environment — shell rc files, global
git config, arbitrary home files. A per-project agent memory directory is
none of those.

**What agentharness should change:** exempt
`<config-dir>/projects/*/memory/` specifically — not the config directory
generally. A global `CLAUDE.md` or `settings.json` one level up is exactly
what the guard exists to protect and must stay blocked.

**Corrective action taken:** fixed in this repo rather than only logged.
The guard now exempts the per-project memory store, honours a relocated
`CLAUDE_CONFIG_DIR`, and keeps blocking everything else under the config
directory. Review caught that the first cut matched
`*/.claude/projects/*/memory/*` anywhere on the filesystem — including
another user's home — so it is now anchored to a single resolved config
root. Five tests, including three asserting the non-memory paths are
still refused. The first cut of the relocated-config test used
`mktemp -d`, which sits under the already-allowed temp root and so passed
without exercising the new branch at all — it now uses a path outside both.

## 2026-08-03 — `audit` describes an install mode that did not exist when it was written

**Where it surfaced:** running `agentharness audit` inside a throwaway
project with the published `agentharness-toolkit@0.6.0` installed from
npm, as an ordinary consumer would.

**What happened:** the validation-commands table reported five of its six
entries as `✗ MISSING` on a completely healthy install. Two lines further
down, the same output reported `Can mechanically enforce the advertised
workflow: true`. The `--json` form agreed with the broken-looking half.

**Why it matters:** nothing was actually wrong. `--mode npm` ships only
`tools/setup/`; the entries being reported missing are the harness repo's
own maintenance scripts, which were never part of the package. A consumer
has no way to know that, and `audit` is precisely the command they would
run to find out whether their install is sound. It answered "mostly
broken" for a correct install, and contradicted itself in the process.

Two adjacent claims in the same table were wrong in *every* install mode,
including a pristine git checkout of this repo:
`tools/verify-content-quality.py` and `tools/generate-manifest.py` are
invoked as `python3 <path>` and are non-executable by design here, so the
blanket `-x` check emitted two `⚠ exists, not executable` warnings that
could not be cleared without making a wrong change. The closing line then
told npm consumers to run `verify-content-quality.py` "in the harness
checkout" — a file not in their package, in a directory they do not have.

**The pattern:** this is the third instance this week of a table of
guarantees outliving the thing it describes. `docs/INTEGRATION.md` had
three false rows, found two at a time. Here the table predates `--mode
npm` entirely. Adding an install mode is not treated as a reason to re-read
every surface that asserts something about "the harness checkout", and the
tests all used the default mode, so nothing caught it.

**What agentharness should change:** when a new install mode is added,
audit every surface that describes the source tree, not just the install
path. More durably: assertions like this table should be scoped by the
mode they apply to at the point they are written, rather than defaulting
to a universal claim that a later mode quietly falsifies.

**Corrective action taken:** fixed rather than only logged. The table is
now scoped per entry (`full` vs `always`) and per invocation style
(`needs_exec`), `--json` gained `requires_executable`, and the
policy-conflict line reports itself unavailable under `--mode npm`. Nine
tests, six of which were verified to fail against the unfixed source and
three of which are counter-cases proving the fix does not over-apply — a
genuinely missing command and a genuinely non-executable script are still
reported.

## 2026-08-03 — `uninstall` leaves empty directories and an undisclosed file

**Where it surfaced:** the same consumer journey, uninstalling from the
throwaway npm project.

**What happened:** uninstall is otherwise clean — it removes every skill,
reverses each managed block, and deletes files it created that held
nothing else. But it left `.claude/`, `.agents/` and `.github/` behind as
empty directories, and left `.agentharness-guarded-paths.json` in place
without mentioning it.

**Why it matters:** small, but it is the difference between "removed" and
"mostly removed". The empty-directory case is a gap in cleanup that
already exists — there is `rmdir` logic, but it only fires on the hooks
path, so it missed the two cases that occur on every single install.
Keeping the guarded-paths file is the *right* call (the operator may have
edited it, and discarding their edits is worse), but keeping it silently
is indistinguishable from a leak to anyone reading the output.

**What agentharness should change:** an uninstall's output should account
for everything it deliberately does not remove. "We kept this and here is
why" is a completed action; saying nothing is an unexplained leftover.

**Corrective action taken:** fixed. Empty parents are pruned with `rmdir`
only, so any directory holding operator-owned content stops the walk
there, and the Python side refuses to climb above the project root. The
guarded-paths file is now disclosed in the output. Four tests, including
a counter-case that fills `.claude/` and `.github/` with operator files
and asserts they survive.

## 2026-08-24 – default "commit-and-stop" authority isn't a safe resting state in ephemeral-container sessions

**Recurrence key:** `ephemeral-container-loses-unpushed-work-on-long-block`

**What happened:** Working an "address gpt-5.6-review.md findings" task
under CLAUDE.md's default Agent Workflow Completion tier (no
`.agentharness-publish-mode`, no standing push authority), a session made
5 individually-verified commits and, per the default tier, left the
branch committed locally and unpushed. It then used `AskUserQuestion` to
escalate a genuinely out-of-scope call (whether to loosen CLAUDE.md's own
self-authorization mandate) rather than deciding unilaterally. The
human's answer arrived in a new session turn on a freshly provisioned
container — `git reflog` showed only a single fresh `checkout` entry, and
`git fetch origin <branch>` returned "couldn't find remote ref": the
branch had never been pushed, so the 5 commits existed nowhere but the
old, now-reclaimed container. No actual work was lost in outcome only
because the same review had, by coincidence, already been completed
independently elsewhere in the same window.

**Root cause:** two individually-reasonable policies compose unsafely.
CLAUDE.md's default authority tier treats "committed locally" as the safe
resting state absent explicit push/PR authorization. The remote-execution
environment's containers are ephemeral and reclaimed after a period of
inactivity. Neither accounts for the other: a local commit is not durable
storage in that environment — only a pushed one survives reclamation —
but the default tier's stop point is *before* push, and `AskUserQuestion`
(or a scheduled check-in) has no bound on how long the container may sit
idle awaiting a human reply, which is exactly the condition that risks
reclamation.

**Impact:** a session doing genuinely unique work under the same
conditions — default tier, ephemeral remote container, a blocking
question with an unbounded wait — would lose that work silently. No
error at commit time, no warning, nothing until a later `git log` looks
unfamiliar.

**What agentharness should change:** CLAUDE.md's default-authority
section should say explicitly that local commits are not a durable
safe-point in an ephemeral-container execution environment, and that a
session about to block on a long-or-unbounded-duration human-input call
with verified, committed-but-unpushed work should either (a) push to a
scratch/WIP branch first — a materially more reversible action than
opening a PR or merging, arguably not needing the same publish authority
under a reasonable reading of the existing tiers — or (b), if push is
genuinely withheld even for a WIP branch, say so explicitly in the
blocking question itself so the human can decide whether to prioritize a
fast reply. This is a policy change to the agent's own default authority,
so it needs an explicit operator decision, not a unilateral edit.

**Corrective action taken:** filed upstream as
[#276](https://github.com/andr-ca/agentharness/issues/276) (single
observed occurrence, not yet corroborated by a second independent
instance — logged per the promotion rule as a candidate finding, not an
immediate mandate change). Note: issue #276 itself claimed this entry
already existed at the time it was filed ("recurrence key
`ephemeral-container-loses-unpushed-work-on-long-block`"); it did not —
this entry was written after triaging the issue and finding the log
missing. That gap is a second, minor data point for the same underlying
class of problem this finding describes (something believed durably
recorded turned out not to be), noted here rather than filed as a
separate issue since it's the same root cause and not yet a second
independent occurrence of a different bug.
