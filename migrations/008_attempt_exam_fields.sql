-- 008: exam attempt fields for olympiad engine
-- expires_at on attempts; saved_at on attempt_answers

ALTER TABLE attempts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS session_token TEXT;

ALTER TABLE attempt_answers ADD COLUMN IF NOT EXISTS saved_at TIMESTAMPTZ DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_attempts_expires ON attempts (expires_at)
  WHERE status = 'in_progress';
