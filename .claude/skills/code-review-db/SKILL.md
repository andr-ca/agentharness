---
name: code-review-db
description: Use when reviewing code that touches the database or persistence layer. Covers index strategy, query count, N+1, transaction scope, migration safety, and connection pooling. Load instead of the general code-review skill for DB-focused reviews.
metadata:
  type: skills
  scope: ["Python", "TypeScript", "Go", "Java", "SQL"]
  when: "Reviewing ORM queries, SQL, migrations, repository classes, or any code path that reads or writes persistent data"
---

# Code Review — Database & Persistence Layer

Focus on performance, correctness, and safety at the data layer.

---

## Query Correctness

- [ ] **N+1 queries** — a loop that loads related records per item. Look for `for item in items: item.related`. Fix with eager loading (`select_related`, `include`, `JOIN`) or a batch fetch outside the loop.
- [ ] **Unbounded queries** — `find_all()`, `SELECT *` with no `LIMIT`, `WHERE 1=1`. Every read from a growing table needs pagination or a `LIMIT`.
- [ ] **Missing WHERE clause** — an `UPDATE` or `DELETE` with no filter deletes/updates every row.
- [ ] **Implicit full-table scan** — a `WHERE` on a column with no index. Check `EXPLAIN` output or migration history.
- [ ] **Fetching more columns than needed** — `SELECT *` when only 2 columns are used. Unnecessary data transfer and harder to cache.

---

## Index Strategy

- [ ] **Missing index on foreign key** — `FK` columns not in an index cause full scans on JOIN and cascade operations.
- [ ] **Missing index on `WHERE`/`ORDER BY` columns** — any column used in a filter, sort, or join should have an index unless the table is tiny (<1k rows).
- [ ] **Index on every column** — over-indexing slows writes. Indexes serve reads; add them only for proven query patterns.
- [ ] **Composite index column order** — a composite index on (A, B, C) helps queries filtering A, or A+B, but NOT B alone. Confirm the index covers the actual query.
- [ ] **Index on high-cardinality boolean** — a boolean column index is almost never useful (50/50 selectivity).

---

## Transactions & Consistency

- [ ] **Two writes without a transaction** — if the second write fails, the first is orphaned. Wrap in a transaction.
- [ ] **Transaction too wide** — a transaction that spans an HTTP call, a file system operation, or a sleep holds locks and causes contention. Keep transactions as short as possible.
- [ ] **Read-your-own-writes** — reading back a record inside a write transaction without using the same transaction/session. Causes stale reads in read-replica setups.
- [ ] **Lost update** — two concurrent reads followed by two concurrent writes without optimistic or pessimistic locking.
- [ ] **Missing rollback on error** — exception handling that logs and continues without rolling back a partially-committed transaction.

---

## Migration Safety

- [ ] **Adding NOT NULL column without default** — will fail on a live table with existing rows. Add with a default, then remove the default in a separate migration.
- [ ] **Renaming a column** — breaks code still pointing to the old name. Dual-write then clean up.
- [ ] **Dropping a column** — ensure no code still reads it before dropping; deploy code first, then migrate.
- [ ] **Adding an index on a large live table** — use `CREATE INDEX CONCURRENTLY` (Postgres) or equivalent to avoid table lock.
- [ ] **Missing index on new FK** — verify the migration adds an index alongside the foreign key constraint.

---

## Connection & Performance

- [ ] **Connection leak** — opening a DB connection without a `with`/`using`/`defer` or a `try/finally`. Connections should always be returned to the pool.
- [ ] **Query in a hot path** — a query inside a render loop, a per-request middleware, or a tight retry loop. Cache or move upstream.
- [ ] **No query timeout** — long-running queries block connections. Always set `statement_timeout` / `command_timeout` in production.

---

## See Also

- `.claude/skills/code-review/SKILL.md` — general review checklist for all layers
- `.claude/skills/design-patterns/SKILL.md` — Repository pattern for isolating DB access
- `.claude/skills/clean-architecture/SKILL.md` — keeping domain logic out of the persistence layer
