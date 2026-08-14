# Phase A — Plain `server_core.py`

## Status (2026-08-14)

- **Live boot:** prefers plain `server_core.py`; if missing, materializes once from `_srv_b64_*.txt`, then runs that file.
- Log line: `[boot] Phase A: server_core.py (from b64) OK`
- Web performance unchanged; only boot path is safer.

## Commit plain core to Git (do this on your PC)

```bash
git clone https://github.com/SharifzodaIbrohim/geogrfia.git
cd geogrfia
python scripts/materialize_server_core.py
# creates server_core.py (~57KB, ~1683 lines)

git add server_core.py
git commit -m "Phase A: commit plain server_core.py (no b64 required for boot)"
git push origin main
```

After this deploy, log should show:

```text
[boot] Phase A: server_core.py (plain) OK
```

without needing materialize.

## Later: remove b64

Only after plain boot is confirmed on Render for several deploys:

1. Keep `_srv_b64_*` one more release as fallback, or
2. Delete `_srv_b64_00.txt` … `_srv_b64_08.txt` and the materialize branch in `server.py`.

Do **not** edit individual b64 chunks by hand.
