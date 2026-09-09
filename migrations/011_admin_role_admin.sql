-- Add operational admin role (all permissions except managing other admins).
DO $mig$
BEGIN
  ALTER TYPE admin_role ADD VALUE IF NOT EXISTS 'admin';
EXCEPTION
  WHEN duplicate_object THEN NULL;
  WHEN others THEN
    -- Older PG without IF NOT EXISTS: ignore if already present
    BEGIN
      ALTER TYPE admin_role ADD VALUE 'admin';
    EXCEPTION WHEN duplicate_object THEN NULL;
    END;
END
$mig$;
