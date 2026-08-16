-- 009: student registration profile fields (admin «Хонандагон»)
ALTER TABLE students ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS patronymic TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS birth_date DATE;
ALTER TABLE students ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS teacher_name TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS photo_data TEXT;
