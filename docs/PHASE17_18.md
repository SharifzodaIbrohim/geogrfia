# Phase 17–18 — Audit + Notifications

## Audit
- Every successful `POST/PUT/PATCH/DELETE` under `/api/admin/*` is logged.
- Also: `admin.login`
- Storage: PostgreSQL `audit_logs` (JSON fallback `data/audit_logs.json`)

`GET /api/admin/audit?limit=100&action=&admin=`

## Notifications (in-app)
- Admin audience notifications for olympiad/quiz create and new results.
- `GET /api/admin/notifications`
- `POST /api/admin/notifications/<id>/read`
- `POST /api/admin/notifications/test`

## Email (optional)
Set on Render:
- `SMTP_HOST`
- `SMTP_PORT` (default 587)
- `SMTP_USER` / `SMTP_PASSWORD`
- `NOTIFY_EMAIL_FROM`
- `NOTIFY_ADMIN_EMAIL` (broadcast to admin inbox)
- `SMTP_TLS=1` (default)

Without SMTP, only in-app notifications work.
