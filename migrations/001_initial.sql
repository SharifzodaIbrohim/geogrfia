-- 001_initial: baseline schema (Phase 1)
-- Equivalent to db/schema.sql at the time of P0.6 formalization.
-- Idempotent: IF NOT EXISTS / DO $$ exception handlers.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$ BEGIN
  CREATE TYPE user_status AS ENUM ('active', 'disabled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE student_status AS ENUM ('active', 'inactive', 'graduated');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE admin_role AS ENUM (
    'super_admin', 'user_admin', 'quiz_admin',
    'olympiad_admin', 'monitor', 'content_admin'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE content_status AS ENUM ('draft', 'published', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE attempt_kind AS ENUM ('quiz', 'olympiad');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE attempt_status AS ENUM (
    'in_progress', 'submitted', 'passed', 'failed', 'timeout', 'cancelled'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT UNIQUE,
  name          TEXT,
  avatar_url    TEXT,
  google_id     TEXT UNIQUE,
  status        user_status NOT NULL DEFAULT 'active',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS schools (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  location    TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS students (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_code TEXT NOT NULL UNIQUE,
  full_name    TEXT NOT NULL,
  class_name   TEXT,
  school_id    UUID REFERENCES schools (id) ON DELETE SET NULL,
  school_name  TEXT,
  user_id      UUID UNIQUE REFERENCES users (id) ON DELETE SET NULL,
  status       student_status NOT NULL DEFAULT 'active',
  created_by   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_students_code ON students (student_code);
CREATE INDEX IF NOT EXISTS idx_students_school ON students (school_id);
CREATE INDEX IF NOT EXISTS idx_students_user ON students (user_id);

CREATE TABLE IF NOT EXISTS admins (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  login         TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL,
  email         TEXT,
  salt          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          admin_role NOT NULL DEFAULT 'super_admin',
  status        user_status NOT NULL DEFAULT 'active',
  created_by    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admins_login ON admins (login);

CREATE TABLE IF NOT EXISTS quizzes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  description TEXT,
  pass_score  INT NOT NULL DEFAULT 70 CHECK (pass_score BETWEEN 0 AND 100),
  time_limit_sec INT,
  is_public   BOOLEAN NOT NULL DEFAULT true,
  status      content_status NOT NULL DEFAULT 'draft',
  created_by  UUID REFERENCES admins (id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quiz_questions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quiz_id    UUID NOT NULL REFERENCES quizzes (id) ON DELETE CASCADE,
  sort_order INT NOT NULL DEFAULT 0,
  text       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz ON quiz_questions (quiz_id);

CREATE TABLE IF NOT EXISTS quiz_options (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID NOT NULL REFERENCES quiz_questions (id) ON DELETE CASCADE,
  sort_order  INT NOT NULL DEFAULT 0,
  text        TEXT NOT NULL,
  is_correct  BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_quiz_options_q ON quiz_options (question_id);

CREATE TABLE IF NOT EXISTS olympiads (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  description TEXT,
  type        TEXT NOT NULL DEFAULT 'olympiad',
  pass_score  INT NOT NULL DEFAULT 70 CHECK (pass_score BETWEEN 0 AND 100),
  duration_sec INT,
  start_at    TIMESTAMPTZ,
  end_at      TIMESTAMPTZ,
  is_active   BOOLEAN NOT NULL DEFAULT false,
  show_public_leaderboard BOOLEAN NOT NULL DEFAULT false,
  hide_names  BOOLEAN NOT NULL DEFAULT false,
  show_school BOOLEAN NOT NULL DEFAULT true,
  show_score  BOOLEAN NOT NULL DEFAULT true,
  status      content_status NOT NULL DEFAULT 'draft',
  created_by  UUID REFERENCES admins (id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (end_at IS NULL OR start_at IS NULL OR end_at > start_at)
);

CREATE INDEX IF NOT EXISTS idx_olympiads_active ON olympiads (is_active, start_at, end_at);

CREATE TABLE IF NOT EXISTS olympiad_questions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  olympiad_id UUID NOT NULL REFERENCES olympiads (id) ON DELETE CASCADE,
  sort_order  INT NOT NULL DEFAULT 0,
  text        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oly_q_oly ON olympiad_questions (olympiad_id);

CREATE TABLE IF NOT EXISTS olympiad_options (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_id UUID NOT NULL REFERENCES olympiad_questions (id) ON DELETE CASCADE,
  sort_order  INT NOT NULL DEFAULT 0,
  text        TEXT NOT NULL,
  is_correct  BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_oly_opt_q ON olympiad_options (question_id);

CREATE TABLE IF NOT EXISTS olympiad_participants (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  olympiad_id UUID NOT NULL REFERENCES olympiads (id) ON DELETE CASCADE,
  student_id  UUID NOT NULL REFERENCES students (id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'assigned',
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (olympiad_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_oly_part_oly ON olympiad_participants (olympiad_id);
CREATE INDEX IF NOT EXISTS idx_oly_part_stu ON olympiad_participants (student_id);

CREATE TABLE IF NOT EXISTS attempts (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kind         attempt_kind NOT NULL,
  quiz_id      UUID REFERENCES quizzes (id) ON DELETE CASCADE,
  olympiad_id  UUID REFERENCES olympiads (id) ON DELETE CASCADE,
  user_id      UUID REFERENCES users (id) ON DELETE SET NULL,
  student_id   UUID REFERENCES students (id) ON DELETE SET NULL,
  student_name   TEXT,
  student_class  TEXT,
  student_school TEXT,
  score        INT,
  correct      INT,
  total        INT,
  pass_score   INT,
  status       attempt_status NOT NULL DEFAULT 'in_progress',
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  CHECK (
    (kind = 'quiz' AND quiz_id IS NOT NULL) OR
    (kind = 'olympiad' AND olympiad_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_attempts_quiz ON attempts (quiz_id);
CREATE INDEX IF NOT EXISTS idx_attempts_oly ON attempts (olympiad_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_student ON attempts (student_id);
CREATE INDEX IF NOT EXISTS idx_attempts_finished ON attempts (finished_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_attempts_oly_student_unique
  ON attempts (olympiad_id, student_id)
  WHERE kind = 'olympiad' AND student_id IS NOT NULL AND status <> 'in_progress';

CREATE TABLE IF NOT EXISTS attempt_answers (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id   UUID NOT NULL REFERENCES attempts (id) ON DELETE CASCADE,
  question_id  UUID NOT NULL,
  selected_idx INT,
  is_correct   BOOLEAN,
  UNIQUE (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action      TEXT NOT NULL,
  admin_id    UUID REFERENCES admins (id) ON DELETE SET NULL,
  admin_login TEXT,
  target_type TEXT,
  target_id   TEXT,
  meta        JSONB,
  ip          TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at DESC);

CREATE TABLE IF NOT EXISTS notifications (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  body        TEXT,
  link        TEXT,
  audience    TEXT NOT NULL DEFAULT 'admin',
  is_read     BOOLEAN NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications (created_at DESC);
