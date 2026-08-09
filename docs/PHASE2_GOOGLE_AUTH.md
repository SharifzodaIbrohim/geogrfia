# Phase 2 — Google OAuth

## Environment (Render)

| Key | Value |
|-----|--------|
| `GOOGLE_CLIENT_ID` | аз Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | ихтиёрӣ (барои code flow) |
| `DATABASE_URL` | аллакай гузоштаед |

## Google Cloud

1. [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials
2. **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Authorized JavaScript origins:
   - `https://geografia-19tf.onrender.com`
   - `http://localhost:5000` (локал)
5. Authorized redirect URIs (агар лозим):
   - `https://geografia-19tf.onrender.com`
6. Client ID-ро нусха → `GOOGLE_CLIENT_ID` дар Render Environment

## API

```
GET  /api/health
GET  /api/auth/google/status   → { configured: true/false, clientId: "..." }
POST /api/auth/google          → { idToken: "..." }
                               ← { user: { id, email, name, avatar } }
```

## Ҷараён

```
Sign in with Google (frontend)
        ↓
id_token
        ↓
POST /api/auth/google
        ↓
verify token (google-auth)
        ↓
upsert users (PostgreSQL / JSON)
        ↓
Geografia session / user object
```

Олимпиада ҳанӯз Student ID талаб мекунад (Phase 3).
