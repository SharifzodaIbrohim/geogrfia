# P0.9 — Secrets & credentials (Geografia)

## Required in production (Render)

| Variable | Purpose | Notes |
|----------|---------|-------|
| `DATABASE_URL` | PostgreSQL | From Render Postgres addon |
| `JWT_SECRET` | Sign admin/user JWTs | Random, **≥32 characters** |

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Optional

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLIENT_ID` | Google Sign-In (Gmail users) |
| `GOOGLE_CLIENT_SECRET` | Server-side OAuth (if used) |
| `USER_SESSION_TTL` | User JWT lifetime (seconds, default 7d) |
| `ADMIN_SESSION_TTL` | Admin JWT lifetime (seconds, default 12h) |
| `GEOGRAFIA_STRICT_SECRETS` | `1` = boot fails if secrets invalid |
| `ALLOW_JSON_BACKEND` | Emergency JSON only — never permanent in prod |

## Rules

1. **Never commit** real passwords, API keys, JWT secrets, or `.env` to git.
2. Production boot **warns** (or **fails** if `GEOGRAFIA_STRICT_SECRETS=1`) when `JWT_SECRET` / `DATABASE_URL` missing or weak.
3. Admin passwords live only in PostgreSQL (`admins.password_hash`), never plaintext.
4. `data/admins.json` is gitignored — use `data/admins.example.json` as a template.
5. Google Client ID comes **only** from env / `/api/auth/google/status` — not hardcoded in JS.

## Render setup checklist

1. Dashboard → Environment:
   - `DATABASE_URL` (linked Postgres)
   - `JWT_SECRET` = output of `token_urlsafe(48)`
   - `GOOGLE_CLIENT_ID` (if needed)
2. Deploy once and open `/api/health` — check:
   ```json
   "secrets": {
     "production": true,
     "databaseUrlSet": true,
     "jwtSecretSet": true,
     "jwtSecretStrong": true
   }
   ```
3. After confirmed strong:
   - set `GEOGRAFIA_STRICT_SECRETS=1`
   - redeploy

## Local development

```bash
cp .env.example .env
# edit .env — JWT_SECRET can be any long random string
```
