# Security layers (P1.1–P1.5)

## P1.3 — Session TTL

| Env | Default | Meaning |
|-----|---------|--------|
| `USER_SESSION_TTL` | `604800` (7d) | Gmail/user JWT + cookie |
| `ADMIN_SESSION_TTL` | `43200` (12h) | Admin JWT + cookie |

Admin sessions are intentionally shorter.

## P1.4 — Rate limiting

| Bucket | Default | Paths |
|--------|---------|-------|
| `admin_login` | 5 / 60s | `POST /api/admin/login` |
| `google_auth` | 10 / 60s | `POST /api/auth/google` |
| `student_login` | 20 / 60s | `POST /api/student/login` |
| `quiz_start` | 10 / 60s | olympiad/quiz start |
| `quiz_submit` | 30 / 60s | olympiad/quiz submit |
| `admin_api` | 120 / 60s | `/api/admin/*` |

Response on limit: **429** + `Retry-After`.

## P1.5 — Security headers

Set on all responses:

- `Strict-Transport-Security` (production)
- `Content-Security-Policy` (+ `frame-ancestors 'none'`)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`

Override CSP via `CONTENT_SECURITY_POLICY` if needed.
