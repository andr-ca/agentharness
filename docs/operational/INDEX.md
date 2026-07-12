# Operational Documents Index

Quick reference for active documents and their status.

## 📋 Active Documents

Currently being researched, developed, or planned:

| Document | Status | Purpose | Location |
|----------|--------|---------|----------|
| (none yet) | - | - | - |

## 🔄 In-Progress Work

Items currently under development:

- (none yet)

## ✅ Completed & Ready

Documents ready to be promoted to harness or archived:

- `reviews/fable-review.md` — full repo review, 2026-07-11. Findings
  consolidated into MANIFEST.md/ROADMAP.md/CHANGELOG.md and the P0/P1/P2
  fixes across the repo; kept here as the historical record rather than
  archived, since `reviews/fable-review-status.md` actively references it.
- `reviews/fable-review-status.md` — disposition of all 30 review
  recommendations. Its two originally-partial items are now done: a real
  logging config loader (`patterns/logging/config_loader.py`, further
  fixed per `reviews/pr4-comments-status.md` item 2) and the sample
  integration project (`examples/sample-project/`). The status doc's
  own per-item verdicts are a dated snapshot and are left as written;
  this note just tracks that both gaps have since closed.
- `reviews/gpt-5.6-review.md` — independent full-repository review dated
  2026-07-11; kept as the historical baseline for its completion audit.
- `reviews/gpt-5.6-review-status.md` — independent re-validation at
  `43604a7`, recorded 2026-07-12T15:47:00Z: 1 of 30 items verified
  complete at that snapshot. Substantial further work against its P1
  backlog (P1-06 through at least P1-12) has landed since that snapshot
  on `chore/add-remaining-components`; the 1-of-30/5.2-10 figures in that
  doc describe the state as of `43604a7`, not current `HEAD` — a fresh
  re-validation pass is owed once the current backlog finishes, rather
  than hand-editing that dated document's tally mid-stream.
- `reviews/pr4-comments-status.md` — disposition and verification record for
  PR #4's review-comment fixes and later coverage/pre-push work.

## 📚 Archives

Historical documents kept for reference:

- (none yet)

## 📝 Adding to This Index

When creating a new operational document:

1. Create the document in appropriate subdirectory (`research/`, `planning/`, etc.)
2. Use format: `{DATE}-{TOPIC}.md` or `{TOPIC}/` directory
3. Add entry to this index with:
   - Document name/path
   - Current status (in-progress, pending-review, completed)
   - Brief purpose
   - When it will be archived or promoted

## 🗑️ Maintenance Schedule

- **Monthly review** – Update this index, archive completed items
- **Quarterly review** – Consolidate findings, promote to harness
- **Yearly archive** – Move old logs and obsolete docs to archives/
