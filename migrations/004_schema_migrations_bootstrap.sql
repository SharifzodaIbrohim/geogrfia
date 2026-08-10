-- 004_schema_migrations_bootstrap: ensure tracking table exists
-- (also created by db.migrate runner; this makes it visible in SQL history)

CREATE TABLE IF NOT EXISTS schema_migrations (
  version     TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  checksum    TEXT,
  applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
