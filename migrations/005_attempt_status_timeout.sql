-- 005: ensure attempt_status includes timeout (idempotent)
-- Runs AFTER 003 so index creation never depends on timeout.

DO $mig$
BEGIN
  ALTER TYPE attempt_status ADD VALUE IF NOT EXISTS 'timeout';
EXCEPTION
  WHEN duplicate_object THEN NULL;
  WHEN undefined_object THEN NULL;
  WHEN others THEN NULL;
END
$mig$;
