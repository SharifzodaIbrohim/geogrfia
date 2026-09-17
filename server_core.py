"""server_core.py — production entry module.

Loads the canonical core from committed `_srv_b64_*.txt` (zlib+base64) into this
module's namespace on import. The decompressed source is the same 1683-line
payload verified against artifacts/STEP1_BOOT/server_core.py (sha256 match).

This keeps `import server_core` working for Step1 boot while the full plain
text can also be materialized offline via scripts/materialize_server_core.py.
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent
_parts = sorted(_dir.glob("_srv_b64_*.txt"))
if not _parts:
    raise RuntimeError("server_core: no _srv_b64_*.txt found")
_raw = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
_src = zlib.decompress(base64.b64decode(_raw)).decode("utf-8")
if "app = Flask" not in _src and "app=Flask" not in _src:
    raise RuntimeError("server_core: decompressed payload has no Flask app")
exec(compile(_src, str(_dir / "server_core.py"), "exec"), globals())
