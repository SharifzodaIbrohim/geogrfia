-- 002: explicit Google binding on students
ALTER TABLE students ADD COLUMN IF NOT EXISTS linked_google_user_id UUID NULL;
ALTER TABLE students ADD COLUMN IF NOT EXISTS linked_at TIMESTAMPTZ NULL;
CREATE INDEX IF NOT EXISTS idx_students_linked_google ON students(linked_google_user_id);
