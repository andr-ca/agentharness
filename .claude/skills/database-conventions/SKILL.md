---
name: database-conventions
description: Use when designing a database schema, writing migrations, reviewing SQL queries, or choosing between relational and document models — covers naming, index strategy, migration safety, N+1 prevention, and transaction boundaries.
metadata:
  type: skills
  complexity: medium
  scope: [all]
---

# Database Conventions

Design and operational guidelines for relational databases (PostgreSQL
primary dialect; MySQL/SQLite notes included where they differ). Apply
these when creating schemas, reviewing migrations, or writing queries.

---

## Naming

- **Tables:** `snake_case`, plural (`users`, `audit_logs`, `order_items`)
- **Columns:** `snake_case`, singular (`user_id`, `created_at`, `is_active`)
- **Primary keys:** `id` (serial/UUID)
- **Foreign keys:** `<referenced_table_singular>_id` (`user_id`, `order_id`)
- **Booleans:** `is_` or `has_` prefix (`is_active`, `has_verified_email`)
- **Timestamps:** `created_at`, `updated_at`, `deleted_at` (UTC, with timezone)

---

## Schema design

- Every table has a primary key. Prefer UUID (`gen_random_uuid()`) for
  distributed or externally-exposed IDs; serial/bigserial for internal
  join tables where IDs never leave the DB.
- Always store timestamps with timezone (`TIMESTAMPTZ` in Postgres).
- Soft-delete via `deleted_at IS NULL` filter, not `DELETE` — unless you
  have a clear data retention policy that requires hard deletes.
- Avoid `TEXT` for constrained values — use an `ENUM` or a lookup table
  so the DB enforces the constraint.

```sql
-- Good: constrained status field
CREATE TYPE order_status AS ENUM ('pending', 'paid', 'shipped', 'cancelled');

CREATE TABLE orders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    status      order_status NOT NULL DEFAULT 'pending',
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Indexes

- Every foreign key column gets an index (Postgres doesn't auto-index FKs).
- Add an index on any column used in a `WHERE`, `ORDER BY`, or `JOIN` in
  frequently-run queries.
- Composite indexes: column order matters — put equality conditions first,
  range/sort columns last.
- Don't index every column — indexes slow writes and consume storage.

```sql
-- Required: FK index
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Composite: user_id first (equality), created_at second (range/sort)
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);
```

---

## Migrations

**Never edit a migration that has been applied anywhere.** Migrations are
immutable once run — treat them like published git commits.

Rules:
- Each migration does one logical change.
- Every migration is reversible — provide a `down` migration.
- Adding a column: always `nullable` or with a `DEFAULT` so existing rows
  are not blocked during migration.
- Renaming a column: two-migration pattern (add new → backfill → drop old)
  to avoid downtime for live deploys.
- Dropping a column or table: mark as `NOT NULL` removal / unused first,
  deploy, then drop in a subsequent release.

```sql
-- WRONG: adds NOT NULL column without a default → fails on existing rows
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20) NOT NULL;

-- RIGHT: nullable first, add default/constraint in a follow-up migration
ALTER TABLE users ADD COLUMN phone_number VARCHAR(20);
```

---

## N+1 queries

N+1 occurs when you load a list of N records and then execute 1 query
per record to load related data.

```python
# WRONG: N+1 — one query for users, then one per user for posts
users = db.query(User).all()
for user in users:
    posts = db.query(Post).filter_by(user_id=user.id).all()  # N queries

# RIGHT: eager load with a JOIN or subquery
users = db.query(User).options(joinedload(User.posts)).all()
```

Detect N+1 in development: log slow queries, use query count assertions
in tests, or use a tool like `sqlalchemy-utils`'s query counter.

---

## Transactions

Use transactions for any multi-step operation where partial completion
would leave the data in an inconsistent state.

```python
# WRONG: transfer without transaction — debit can succeed while credit fails
account_a.balance -= amount
account_b.balance += amount

# RIGHT: wrap in a transaction
with db.begin():
    account_a.balance -= amount
    account_b.balance += amount
```

Rules:
- Keep transactions as short as possible — hold locks for the minimum time.
- Don't make external HTTP calls inside a transaction.
- Read-only queries don't need transactions (but `REPEATABLE READ` isolation
  may be appropriate for consistent multi-query reads).

---

## Query review checklist

- [ ] All user-supplied values in parameterised queries (no string interpolation)
- [ ] Foreign keys are indexed
- [ ] `SELECT *` replaced with explicit column list in production queries
- [ ] Pagination uses `LIMIT` + `OFFSET` or cursor-based (prefer cursor for large sets)
- [ ] No N+1 pattern in loops
- [ ] Multi-step writes wrapped in a transaction
- [ ] Migrations are reversible and don't add NOT NULL columns without defaults
