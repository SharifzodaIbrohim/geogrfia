-- 002_student_google_link: explicit Google binding columns on students
-- Complements users.google_id + students.user_id FK from 001.

ALTER TABLE students ADD COLUMN IF NOT EXISTS linked_google_user_id UUID NULL;
ALTER TABLE students ADD COLUMN IF NOT EXISTS linked_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_students_linked_google ON students (linked_google_user_id);
