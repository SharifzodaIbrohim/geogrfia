-- 003_exam_integrity: one finished attempt per student per olympiad
-- Use only statuses that exist on both old and new attempt_status enums.
-- (timeout may be missing on databases created before full schema.)

CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_student_olympiad
  ON attempts (student_id, olympiad_id)
  WHERE olympiad_id IS NOT NULL
    AND student_id IS NOT NULL
    AND status IN ('passed', 'failed', 'submitted');
