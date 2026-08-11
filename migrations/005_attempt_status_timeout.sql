-- 005: ensure attempt_status has 'timeout' (safe on already-updated DBs)

DO $mig$
BEGIN
  ALTER TYPE attempt_status ADD VALUE IF NOT EXISTS 'timeout';
EXCEPTION
  WHEN duplicate_object THEN NULL;
  WHEN undefined_object THEN NULL;
END
$mig$;
