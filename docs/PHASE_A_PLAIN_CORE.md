# Phase A+ — Plain `server_core.py` (production default)

## Status (2026-09-17 — Step 1 Boot Stabilization)

- **Production default:** import/load committed plain `server_core.py`.
- **No runtime b64 materialize** unless `GEOGRAFIA_ALLOW_B64_BOOT=1` (or non-production and plain missing).
- Log on healthy boot: `[boot] Phase A: server_core.py (import) OK`
- `_srv_b64_00.txt` … `_srv_b64_08.txt` remain in repo as **emergency recovery only**. Do not delete yet.

## Boot order (`server.py`)

1. `import server_core` (preferred)
2. Else exec committed `server_core.py` file content (no generation)
3. Else, only if `GEOGRAFIA_ALLOW_B64_BOOT=1` (or non-prod): materialize from `_srv_b64_*` then exec

## One-time / local materialize (does not change production default)

```bash
python scripts/materialize_server_core.py
# writes server_core.py (~57KB, ~1683 lines)
git add server_core.py
git commit -m "Phase A+: commit plain server_core.py (production boot source)"
```

## Emergency recovery

```bash
# only when plain core is broken and you need to boot
export GEOGRAFIA_ALLOW_B64_BOOT=1
gunicorn server:app -b 127.0.0.1:8000
```

## Later cleanup (not Step 1)

Only after plain boot is confirmed on Render for several deploys:

1. Keep `_srv_b64_*` one more release as fallback, then
2. Optionally remove materialize path and b64 chunks.

Do **not** edit individual b64 chunks by hand.
