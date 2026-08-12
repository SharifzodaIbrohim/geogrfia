# PHASE 25.5 — Gap Closure

## Status (2026-08-12)

### P0 Done
- [x] P0.1 / **25.5.1 Architecture cleanup**: remote `urllib`+`exec` removed. `server.py` boots only from local `_srv_b64_*.txt` (zlib+base64). No network at boot. No GitHub load.
- [x] P0.2 Real `olympiad_engine.py` + `quiz_api.py` (no PLACEHOLDER)
- [x] P0.3 Olympiad access: empty participants ≠ open; Student ID required for type=olympiad
- [x] P0.5 Production requires `DATABASE_URL` (JSON only with `ALLOW_JSON_BACKEND=1`)
- [x] P0.6 Migrations folder (`migrations/001–008`)
- [x] P0.7 RBAC: unknown role → deny (never escalate to super_admin)
- [x] P0.8 Super-admin last-admin protection + role change audit
- [x] P0.9 JWT_SECRET required in production; configurable session TTL

### Architecture Freeze (25.5.1)
- `server.py` = thin local loader only
- Payload = `_srv_b64_00.txt` + `_srv_b64_01.txt` (compressed expanded source)
- Zero `urllib.request` / `raw.githubusercontent` at runtime boot
- All P1 installs (session, rate limit, headers, one_attempt, force_public_quiz_list) embedded in payload

### P1 Done (summary)
Session cookies, logout/jti revocation, TTL, rate limits, security headers, audit, olympiad attempts engine, server timer, one-attempt, public questions sanitize.
