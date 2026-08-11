-- 003_exam_integrity: one finished attempt per student per olympiad
-- Use only status values that exist on all environments.
-- (Some prod DBs were created before 'timeout' was added to attempt_status.)

CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_student_olympiad
  ON attempts (student_id, olympiad_id)
  WHERE olympiad_id IS NOT NULL
    AND student_id IS NOT NULL
    AND status IN ('passed', 'failed', 'submitted');
