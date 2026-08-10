-- 003_exam_integrity: one finished attempt per student per olympiad
-- (in_progress rows may still exist; uniqueness only for terminal statuses)

CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_student_olympiad
  ON attempts (student_id, olympiad_id)
  WHERE olympiad_id IS NOT NULL
    AND student_id IS NOT NULL
    AND status IN ('passed', 'failed', 'submitted', 'timeout');
