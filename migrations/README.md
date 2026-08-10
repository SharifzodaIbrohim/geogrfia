# Geografia — versioned migrations (P0.6)

## Rules

1. **Never edit an already-applied migration** on production. Add `005_*.sql` instead.
2. Filename: `NNN_short_snake_name.sql` (3+ digit version prefix).
3. SQL must be **idempotent** where possible (`IF NOT EXISTS`, `DO $$ … EXCEPTION`).
4. `db/schema.sql` is the **documentation baseline** (full picture).  
   **Applied state** is only what is recorded in `schema_migrations`.
5. Data backfill (JSON → PG) stays in `scripts/migrate_json_to_pg.py` — not in SQL migrations.

## Commands

```bash
export DATABASE_URL=postgresql://...

python -m db.migrate --status   # list applied / pending
python -m db.migrate --dry-run  # show what would run
python -m db.migrate            # apply pending
```

## Boot

On app start (when `DATABASE_URL` is set), `db.migrate.run_migrations()` may run automatically  
to apply pending versions. Safe and idempotent.

## Current chain

| Version | File | Purpose |
|--------|------|--------|
| 001 | `001_initial.sql` | Baseline tables, enums, indexes |
| 002 | `002_student_google_link.sql` | Google link columns on students |
| 003 | `003_exam_integrity.sql` | One finished attempt per student/olympiad |
| 004 | `004_schema_migrations_bootstrap.sql` | Tracking table (also created by runner) |
