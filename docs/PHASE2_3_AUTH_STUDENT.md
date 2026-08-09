# Phase 2 (JWT) + Phase 3 (Student ID)

## Env (Render)

| Key | Value |
|-----|--------|
| `JWT_SECRET` | рамзи дарози тасодуфӣ (ҳатмӣ барои production) |
| `GOOGLE_CLIENT_ID` | аллакай гузоштаед |
| `DATABASE_URL` | аллакай |

## Phase 2 — Tokens

- User: `X-User-Token` (JWT, 7 рӯз)
- Admin: `X-Admin-Token` (JWT, 12 соат)
- Дигар in-memory token нест — multi-worker Render OK

## Phase 3 — Student ID

| API | Тавсиф |
|-----|--------|
| `POST /api/student/link` | Google user + `{ "studentId": "..." }` → `students.user_id` |
| `GET /api/student/me` | profile: Google user + linked student |
| `POST /api/admin/olympiads/<id>/participants` | `{ "studentIds": ["code", ...] }` |
| `GET /api/admin/olympiads/<id>/participants` | рӯйхати assignment |
| `POST /api/olympiads/<id>/access` | `{ "studentId" }` → оё иҷозат дорад |

### Access rule (олимпиада)

1. Олимпиада open (active + time window)
2. Student code дуруст
3. Агар барои ин олимпиада **ҳеҷ** participant нест → ҳамаи student-ҳои active (мувофиқи legacy)
4. Агар participant ҳаст → танҳо assigned
5. Ихтиёрӣ: linked Google (`user_id`) барои profile; exam ҳоло бо studentId

### Тартиби навбатӣ (нақша)

Phase 4–5: Super Admin + RBAC enforcement
