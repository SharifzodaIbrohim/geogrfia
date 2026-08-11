# P0.9 — Secrets & credentials (Geografia)

## Required in production (Render)

| Variable | Purpose | Notes |
|----------|---------|-------|
| `DATABASE_URL` | PostgreSQL | Provided by Render Postgres |
| `JWT_SECRET` | Sign admin/user JWT | Random, **≥32 characters** |

Generate JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Optional

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLIENT_ID` | Google Sign-In |
| `GOOGLE_CLIENT_SECRET` | Google OAuth (if server-side) |
| `USER_SESSION_TTL` | User JWT lifetime (seconds, default 7d) |
| `ADMIN_SESSION_TTL` | Admin JWT lifetime (seconds, default 12h) |
| `ALLOW_JSON_BACKEND` | Emergency JSON fallback (`1` only) — never in prod normally |

## Rules

1. **Never commit** real passwords, API keys, or JWT secrets to git.
2. Production boot **refuses** weak/missing `JWT_SECRET` and missing `DATABASE_URL`.
3. Admin passwords live only in the `admins` table (hashed); reset via Super Admin or DB.
4. Default seed password for local only — change immediately on any shared environment.

## Render checklist

Environment → add:

- `JWT_SECRET` = (output of token_urlsafe)
- `DATABASE_URL` = (from Postgres addon)
- `GOOGLE_CLIENT_ID` = (if Gmail login needed)

Redeploy after setting secrets.
