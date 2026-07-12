---
description: Comprehensive git branching strategy, prefixes, worktrees, and gitignore guidelines
applyTo: all projects using agentharness
---

# Branching Strategy

Complete guide to branching discipline, naming conventions, worktrees, and git configuration for sustainable development.

## 🚫 Core Rule: Never Commit to Trunk

### What is "Trunk"?

Trunk branches are the main integration branches:
- `main` – Production-ready code
- `master` – Legacy production branch
- `trunk` – Some projects use this naming
- `develop` – Development integration branch (if used)
- `release/*` – Release branches

### The Rule

**You must NEVER directly commit to trunk branches.**

Instead:
1. Create a feature branch off trunk
2. Make your changes on that branch
3. Create a pull request
4. Get reviewed
5. Merge back to trunk via PR

### Why This Matters

- **History clarity** – Trunk shows only merged features and fixes, not partial work
- **Rollback safety** – Bad commits can be reverted without losing other work
- **Code review** – All code on trunk is reviewed
- **CI/CD safety** – Trunk is assumed stable and can trigger deployments
- **Bisecting** – Finding bugs in history is easier with clean commits
- **Recovery** – You can always rebase your branch on trunk if needed

### Enforcing This Rule

Configure your repository to prevent direct commits:

```bash
# Via GitHub: Settings > Branches > Branch Protection Rules
# - Require pull request reviews
# - Require status checks to pass
# - Require branches to be up to date before merging

# Via git hooks:
# Create .git/hooks/pre-commit or .husky/pre-commit
```

Example pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit or in .husky/pre-commit

TRUNK_BRANCHES=("main" "master" "develop")
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

for trunk in "${TRUNK_BRANCHES[@]}"; do
    if [ "$CURRENT_BRANCH" = "$trunk" ]; then
        echo "❌ Cannot commit directly to $trunk"
        echo "Create a feature branch first:"
        echo "  git checkout -b feature/your-feature"
        exit 1
    fi
done

exit 0
```

## 📋 Branch Naming Convention

### Format

```
{type}/{scope}/{description}
```

### Branch Type Prefixes

Use consistent prefixes to categorize work:

| Type | Purpose | Example |
|------|---------|---------|
| `feature/` | New feature or enhancement | `feature/user-authentication` |
| `fix/` | Bug fix | `fix/email-validation-crash` |
| `refactor/` | Code refactoring (no behavior change) | `refactor/simplify-user-service` |
| `test/` | Testing improvements | `test/add-integration-tests` |
| `docs/` | Documentation changes | `docs/update-readme` |
| `chore/` | Maintenance, deps, config | `chore/upgrade-dependencies` |
| `perf/` | Performance improvement | `perf/optimize-query-caching` |
| `ci/` | CI/CD changes | `ci/add-coverage-reporting` |
| `wip/` | Work in progress (don't merge!) | `wip/exploring-new-approach` |

### Naming Rules

- **Use lowercase** – All branch names in lowercase
- **Use hyphens, not underscores** – Prefer `user-auth` not `user_auth`
- **Be descriptive** – `feature/user-authentication` not `feature/update`
- **Keep it short** – Aim for under 50 characters total
- **Include issue number when available** – `feature/user-auth-#123`
- **Avoid special characters** – Only letters, numbers, hyphens

### Good vs. Bad Branch Names

**Good** ✅
```
feature/user-authentication
fix/email-validation-#123
refactor/simplify-user-service
docs/api-endpoint-guide
perf/optimize-database-queries
```

**Bad** ❌
```
user-auth                          # Missing type prefix
Feature/UserAuthentication         # Mixed case
feature/user_authentication        # Underscore instead of hyphen
feature/update                     # Too vague
fix_everything_#123                # Underscore instead of hyphen
WIP-new-stuff                      # Capitalized, not marked properly
```

## 🌿 Branch Workflow

### Creating a Branch

```bash
# Ensure you're on trunk and up-to-date
git checkout main
git pull origin main

# Create and switch to feature branch
git checkout -b feature/your-feature

# Or in one command (Git 2.23+)
git switch -c feature/your-feature
```

### Working on Your Branch

```bash
# Make changes, stage them
git add src/file.js

# Commit with clear message
git commit -m "Add user authentication middleware"

# Keep updated with trunk
git fetch origin
git rebase origin/main

# If changes conflict, resolve and continue
git rebase --continue
```

### Pushing Your Branch

```bash
# First push (sets up tracking)
git push -u origin feature/your-feature

# Subsequent pushes
git push

# Force push only after rebase (use carefully!)
git push --force-with-lease origin feature/your-feature
```

### Creating a Pull Request

1. Push your branch
2. Go to repository on GitHub/GitLab
3. Click "Create Pull Request"
4. Fill in title and description
5. Request reviewers
6. Wait for CI and review
7. Merge via PR (usually "Squash and Merge" or "Create a Merge Commit")

### After Merging

```bash
# Delete your local branch
git branch -d feature/your-feature

# Delete remote branch (usually auto-deleted by GitHub)
git push origin --delete feature/your-feature

# Or use GitHub UI to delete after merge

# Verify it's gone
git branch -a | grep your-feature  # Should show nothing
```

## 🔧 Git Worktrees

Git worktrees let you work on multiple branches simultaneously without switching. Each worktree is a separate working directory.

### When to Use Worktrees

**Use worktrees when:**
- You need to frequently switch between branches
- You're comparing two versions side-by-side
- You want to run tests on one branch while coding on another
- You're reviewing a PR while working on something else
- Switching branches is slow (large repos)

**Don't use for:**
- Quick edits on a single branch
- Simple feature work
- When context is low (just a couple branches)

### Creating a Worktree

```bash
# Create worktree for new branch
git worktree add ../feature-auth feature/user-authentication

# Or create new branch and worktree together
git worktree add -b feature/new-feature ../feature-new origin/main

# List all worktrees
git worktree list

# Remove worktree
git worktree remove ../feature-auth

# Or with prune if worktree directory is deleted
git worktree prune
```

### Worktree Directory Structure

```
your-project/
├── .git                          # Main repository
├── src/
├── .worktrees/                   # All worktrees in one place
│   ├── main/                     # Worktree on main branch
│   ├── feature-auth/             # Worktree on feature branch
│   ├── feature-payment/          # Another feature branch
│   └── fix-bug-123/              # Bug fix branch
├── .gitignore
└── ...
```

### Best Practices for Worktrees

**1. Keep worktrees in a separate directory:**

```bash
# Create worktrees in .worktrees/ subdirectory
mkdir -p .worktrees
git worktree add .worktrees/feature-auth feature/user-auth

# Or use relative paths
git worktree add ../repo-branch-name feature/your-feature
```

**2. Use consistent naming:**

```bash
# Structure: .worktrees/{branch-name}/
git worktree add .worktrees/feature-auth feature/user-auth
git worktree add .worktrees/fix-crash-123 fix/email-validation-crash
```

**3. Don't share worktree folders:**

```bash
# Each worktree gets its own directory
git worktree add .worktrees/feature-one feature/one
git worktree add .worktrees/feature-two feature/two

# NOT this:
git worktree add .worktrees/features feature/one  # Bad!
```

**4. Clean up when done:**

```bash
# Remove worktree
git worktree remove .worktrees/feature-auth

# Or if directory was manually deleted
git worktree prune

# Verify it's gone
git worktree list
```

### Worktree Workflow Example

```bash
# Main repository working on main
cd my-project

# Create worktree for feature development
git worktree add .worktrees/feature-auth feature/user-auth

# In another terminal, work on the feature
cd my-project/.worktrees/feature-auth
nano src/auth.js
git add .
git commit -m "Add authentication"
git push

# Back in main directory, work on different feature
cd my-project  # Still on main
git worktree add .worktrees/fix-issue fix/email-validation

# Now you have two worktrees running simultaneously
# Terminal 1: .worktrees/feature-auth/
# Terminal 2: .worktrees/fix-issue/
# Terminal 3: original my-project/ (on main)

# Clean up when done
git worktree remove .worktrees/feature-auth
git worktree remove .worktrees/fix-issue
```

## 🚫 .gitignore Configuration

### What to Ignore

Your `.gitignore` should exclude:

1. **Worktree directories** (if kept at project root)
2. **IDE and editor files**
3. **OS files**
4. **Installed dependencies** (`node_modules/`, `venv/`, etc. — not lock files)
5. **Build artifacts**
6. **Environment variables** (`.env` and its variants — not `.env.sample`)
7. **Temporary files**

Lock files (`package-lock.json`, `Gemfile.lock`, `go.sum`, …) and version-pin
files (`.nvmrc`, `.python-version`, …) are **committed**, not ignored — they
make builds reproducible across machines and CI.

### Comprehensive .gitignore Template

Don't duplicate the template here — it drifts. The canonical, maintained
version lives at `.github/.gitignore.template`. Copy it into your project:

```bash
cp .github/.gitignore.template your-project/.gitignore
```

See that file for the full template and its policy notes (lock files and
version-pin files are committed, not ignored; `.env.sample` is committed,
`.env` is not).


### Environment Variable Pattern

Never commit `.env` but DO commit `.env.sample`:

```bash
# Create sanitized example
cp .env .env.sample

# Remove all secrets from .env.sample
# Replace values with placeholders
# DATABASE_URL=postgresql://localhost/db
# API_KEY=your_api_key_here
# SECRET_TOKEN=your_secret_token

# Commit
git add .env.sample
git commit -m "Add environment variable template"

# Ensure .env is ignored
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
```

### Verify Gitignore Works

```bash
# Check if file is ignored
git check-ignore -v .env

# List all ignored files
git status --ignored

# Check what would be added (including ignored)
git add -n .  # Dry run of git add

# Actually git add (respects .gitignore)
git add .

# Force add ignored file (don't do this!)
git add -f .env  # Only if you really need to (rare)
```

## 🔐 Protecting Secrets

### Before Pushing

```bash
# Check staged/unstaged diffs for common secret patterns
git diff | grep -iE "password|api[_-]?key|secret|token" 
git diff --cached | grep -iE "password|api[_-]?key|secret|token"

# List the 10 largest files in history (binary secrets are often oversized)
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '/^blob/ {print $3, $4}' |
  sort -rn | head -10
```

### If You Accidentally Committed Secrets

**Act immediately — and rotate the secret regardless of whether history cleanup succeeds. A secret that touched git history must be treated as compromised.**

**Preferred: BFG Repo Cleaner** (`brew install bfg` or download the jar) — much faster and safer than `filter-branch`:

```bash
# 1. Clone a fresh mirror (BFG operates on a bare mirror clone, not your working copy)
git clone --mirror git@github.com:you/your-repo.git repo-mirror.git
cd repo-mirror.git

# 2. Delete the file by name from all of history
bfg --delete-files .env

# 3. Clean up and push the rewritten history to every branch
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force

# 4. Everyone with a clone must re-clone or hard-reset — rewritten history
#    doesn't merge cleanly with old clones.
```

**Fallback (no BFG available): `git filter-repo`** (the modern, maintained
replacement for `filter-branch`, which is slow and easy to misuse):

```bash
git filter-repo --path .env --invert-paths
git push --force
```

**Either way:**
1. Rotate the leaked secret immediately — assume it's compromised even after cleanup, since caches, forks, and CI logs may still hold the old history.
2. Notify anyone with a clone to re-clone rather than pull.
3. Add the file to `.gitignore` (or `!.env.sample`-style negation) so it can't be re-committed.

## 📊 Branch Lifecycle

### Example: Feature Branch Lifecycle

```
1. Create
   git checkout -b feature/user-auth

2. Development
   git add src/auth.js
   git commit -m "Add authentication"
   git push -u origin feature/user-auth

3. Keep Updated
   git fetch origin
   git rebase origin/main

4. Push Updates
   git push --force-with-lease

5. Create PR
   GitHub: New Pull Request

6. Review & CI
   - Automated tests run
   - Code review feedback
   - Make changes if needed

7. Merge
   - Squash and merge (clean history)
   - Or create merge commit (preserve history)

8. Cleanup
   git branch -d feature/user-auth
   git push origin --delete feature/user-auth
```

## 🎯 Best Practices Summary

### DO ✅

- ✅ Create a branch for every change
- ✅ Use consistent prefix naming
- ✅ Keep branch names short and descriptive
- ✅ Push regularly so work isn't lost
- ✅ Rebase on trunk to stay up-to-date
- ✅ Use worktrees for complex multi-branch work
- ✅ Delete branches after merging
- ✅ Verify `.gitignore` catches secrets
- ✅ Use `--force-with-lease` instead of `--force`
- ✅ Reference issues in branch names and commits

### DON'T ❌

- ❌ Commit directly to main/master/trunk
- ❌ Use vague branch names like "update" or "fix"
- ❌ Leave orphaned branches (delete after merge)
- ❌ Commit secrets, passwords, API keys
- ❌ Merge without PR review
- ❌ Use `git push --force` (use `--force-with-lease` instead)
- ❌ Leave worktrees behind when deleting them
- ❌ Ignore `.gitignore` violations
- ❌ Have multiple worktrees on the same branch
- ❌ Rebase public/shared branches

## 🔗 Integration with agentharness

Projects should:
1. Apply this branching strategy to all repositories
2. Configure branch protection on main/master
3. Set up `.gitignore` using the template above
4. Enforce commit signing and hook requirements (see COMMITTING_GUIDELINES.md)
5. Require PR reviews before merging (GitHub Settings)

### Project Setup

```bash
# 1. Copy branching strategy guide to project
cp .github/BRANCHING_STRATEGY.md your-project/

# 2. Add comprehensive .gitignore
cp .github/.gitignore.template your-project/.gitignore

# 3. Set up pre-commit hook to prevent trunk commits
cp .github/hooks/prevent-trunk-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 4. Create .worktrees/ directory
mkdir -p .worktrees
echo ".worktrees/" >> .gitignore

# 5. Configure branch protection via GitHub UI
# Settings > Branches > Add Rule for main
```

## ❓ FAQ

**Q: Can I commit directly to main in emergencies?**  
A: No. Even urgent fixes should go through a branch and PR. If truly critical, use a fast-track process but still require review.

**Q: How many worktrees is too many?**  
A: Usually 2-3 max. More than that and you should close some and clean up.

**Q: What if I created a worktree but forgot to use it?**  
A: Just delete it: `git worktree remove .worktrees/forgotten-branch` or `git worktree prune`

**Q: Can I share a worktree directory?**  
A: No, each branch needs its own worktree directory. Sharing causes conflicts.

**Q: What's the difference between `--force` and `--force-with-lease`?**  
A: `--force-with-lease` is safer—it fails if someone else pushed after you fetched. Use this instead of `--force`.

**Q: How do I recover a deleted branch?**  
A: Git keeps reflog for 30 days: `git reflog` and `git checkout <commit-hash>`

**Q: Should I commit lock files?**  
A: Yes (usually). Lock files (`package-lock.json`, `poetry.lock`, etc.) ensure reproducible builds.

---

**Last Updated:** 2026-07-11  
**See Also:** COMMITTING_GUIDELINES.md, CODING_GUIDELINES.md
