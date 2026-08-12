# PHASE 25.5 — Gap Closure

## Status (2026-08-12)

### 25.5.1 Architecture cleanup — DONE (local)
- `server.py` is a **local-only loader** (no `urllib`, no `raw.githubusercontent`, no network at boot).
- Payload resolution order:
  1. `_srv_b64_*.txt` (zlib + base64)
  2. `server_core_part*.py`
  3. `server_core.py`
- Expanded payload (1684 lines, dual-mode core + all P1 patches) is generated and verified in workspace `artifacts/`.
- **Deploy note:** Render/prod must include the payload files next to `server.py`. Without them boot raises `RuntimeError` (fail-closed).

### P0 Done
- [x] P0.1 / 25.5.1 remote exec removed
- [x] P0.2 Real olympiad_engine + quiz_api
- [x] P0.3 Empty participants = locked; Student ID required
- [x] P0.5 DATABASE_URL required in production
- [x] P0.6 Migrations 001–008
- [x] P0.7 RBAC deny-unknown
- [x] P0.8 Super-admin last-admin protection
- [x] P0.9 Secrets / JWT strict in prod

### Architecture Freeze target
No remote code loading · real engines · strict olympiad access · PG production-only · default-deny RBAC.
