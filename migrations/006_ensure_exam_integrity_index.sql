-- 006: guarantee one-finished-attempt index exists
-- Safe even if 003 was recorded with an older checksum / partial apply.

CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_student_olympiad
  ON attempts (student_id, olympiad_id)
  WHERE olympiad_id IS NOT NULL
    AND student_id IS NOT NULL
    AND status IN ('passed', 'failed', 'submitted');
