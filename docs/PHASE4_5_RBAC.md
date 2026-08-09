# Phase 4–5 — Super Admin + RBAC

## Roles

| Role | Permissions |
|------|-------------|
| `super_admin` | ҳама |
| `user_admin` | students, schools, admins.read |
| `quiz_admin` | quizzes, results.read |
| `olympiad_admin` | olympiads, participants, results, monitor, students.read |
| `monitor` | monitor, results, olympiads.read, students.read |
| `content_admin` | content (countries/books) |

## API

- JWT admin token includes `role`
- `GET /api/admin/me` → admin + role + permissions
- `POST /api/admin/admins` body may include `role` (only super_admin)
- `PATCH /api/admin/admins/<id>/role` `{ "role": "monitor" }` (super only)
- Forbidden → 403 with message

## Env

`JWT_SECRET` must be set (already).
