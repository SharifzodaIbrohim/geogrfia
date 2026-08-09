# Phase 8 — Quiz Platform

## Access modes

| Mode | Who can take |
|------|----------------|
| `public` | Anyone |
| `google` | Signed-in Google user |
| `school` | Student ID (optional schoolName match) |

## APIs

### Public / user
- `GET /api/quizzes` — published list (no answers)
- `GET /api/quizzes/<id>` — questions without answers (access checked)
- `POST /api/quizzes/<id>/start` — `{ studentId? }` + optional `X-User-Token` → attempt + timer
- `POST /api/quizzes/<id>/submit` — `{ attemptId, answers: [{questionId, selected}] }` → **server score**
- `GET /api/me/quiz-history` — requires `X-User-Token`

### Admin (quiz_admin / super_admin)
- `GET /api/admin/quizzes`
- `POST /api/admin/quizzes` — create with questions, accessMode, timeLimitSec
- `DELETE /api/admin/quizzes/<id>`
- `PATCH /api/admin/quizzes/<id>` — status draft/published/archived

## Timer
`timeLimitSec` on quiz. `start` returns `endsAt`. Submit after deadline still scores but `timedOut: true` (15s grace).

## Scoring
Never trust client score. Correct answers only on server.
