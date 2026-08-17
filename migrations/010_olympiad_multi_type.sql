-- 010: multi-type olympiad questions + results visibility
ALTER TABLE olympiads ADD COLUMN IF NOT EXISTS questions_json JSONB;
ALTER TABLE olympiads ADD COLUMN IF NOT EXISTS show_results_to_students BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE olympiad_questions ADD COLUMN IF NOT EXISTS qtype TEXT NOT NULL DEFAULT 'single';
ALTER TABLE olympiad_questions ADD COLUMN IF NOT EXISTS payload JSONB;
