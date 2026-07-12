---
name: committing
description: Use when creating a git commit — atomic commits, message format, what never to commit, and the agent workflow-completion requirement (commit → push → PR).
metadata:
  type: skills
  complexity: low
---

# Committing

Full reference: `.github/COMMITTING_GUIDELINES.md` (examples, git aliases,
commit template). This skill is the actionable summary.

## Before you commit

1. `git status` and `git diff` — know exactly what you're about to commit.
2. Stage specific files, not `git add .` / `git add -A` blind.
3. `git diff --cached` — review staged content one more time, scan for
   secrets (API keys, tokens, passwords).
4. Let hooks run. Never `--no-verify`, never `--no-gpg-sign`. If a hook
   fails, fix the underlying issue and re-stage — don't bypass it.

## Writing the commit

- **Atomic**: one logical change per commit. Don't mix a feature, a fix,
  and a refactor in one commit.
- **Message explains WHY, not WHAT** — the diff already shows what
  changed.
- Imperative mood summary ("Add X", not "Added X"), ideally under ~50
  chars, blank line, then body wrapped at ~72 chars if more explanation
  is needed.
- Reference issues (`Fixes #123`, `Relates to #456`) when applicable.

## What never gets committed

- Secrets: API keys, tokens, passwords, private credentials.
- `.env` and its variants — but DO commit `.env.sample` (sanitized
  template).
- Debug code: stray `console.log`/`print`, commented-out code, debugger
  statements.
- Build artifacts, `node_modules/`, and anything covered by
  `.github/.gitignore.template`.

## After the commit — mandatory for agents

This harness's `CLAUDE.md` mandates the full workflow: commit → push →
PR. Don't stop at the commit.

1. `git push -u origin <branch>` (first push) or `git push` (subsequent).
2. `gh pr create` with a real title, body, and test/verification notes.
3. Work is not "done" until the PR exists and its link has been given to
   the user. An agent claiming completion without a PR is incomplete —
   see `CLAUDE.md`'s "Agent Workflow Completion" section.

## If tests or hooks fail

Fix the underlying issue (lint error, failing test, secret detected).
Don't commit broken code planning to fix it "in the next commit."
