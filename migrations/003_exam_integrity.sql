-- 003: one official attempt integrity helpers
CREATE UNIQUE INDEX IF NOT EXISTS uq_attempt_student_olympiad
  ON attempts (student_id, olympiad_id)
  WHERE olympiad_id IS NOT NULL AND status IN ('passed','failed','submitted');
