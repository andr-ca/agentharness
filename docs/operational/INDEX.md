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
  recommendations. Both items originally left partial (logging config
  loader, sample integration project) are now implemented — see
  `ROADMAP.md`'s "Explicitly Deferred" section — so this is now a
  historical record rather than an active item, same as the review above.
- `reviews/gpt-5.6-review.md` — independent second-opinion review,
  dated 2026-07-11, filed against PR #4's branch.
- `reviews/gpt-5.6-review-status.md` — disposition of the review above.
  Stays active until P0-03 (self-authorization mandate) is decided; the
  P1/P2 items it defers are tracked in `ROADMAP.md`.
- `reviews/pr4-comments-status.md` — disposition of Copilot's PR #4
  review comments plus a fable-review-status audit gap.

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
