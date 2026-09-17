"""Geografia entry - Phase A: plain server_core.py preferred (no network at boot)."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except Exception:
    pass

_dir = Path(__file__).resolve().parent
_boot_mode = None
app = None


def _exec_src(src: str, label: str) -> None:
    global app, _boot_mode
    g = globals()
    exec(compile(src, "server_core.py", "exec"), g)
    if g.get("app") is None:
        raise RuntimeError(f"{label}: Flask app not defined")
    app = g["app"]
    _boot_mode = label
    print(f"[boot] Phase A: {label} OK")


def _load_b64_src() -> str:
    parts = sorted(_dir.glob("_srv_b64_*.txt"))
    if not parts:
        raise RuntimeError("no _srv_b64_*.txt")
    raw = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    return zlib.decompress(base64.b64decode(raw)).decode("utf-8")


def _materialize_core_from_b64() -> Path:
    src = _load_b64_src()
    if "app = Flask" not in src and "app=Flask" not in src:
        raise RuntimeError("b64 payload has no Flask app")
    out = _dir / "server_core.py"
    out.write_text(src, encoding="utf-8")
    print(f"[boot] materialized {out.name} ({len(src)} chars)")
    return out


_core = _dir / "server_core.py"
if _core.is_file() and _core.stat().st_size > 10000:
    try:
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (plain)")
    except Exception as e:
        print("[boot] plain server_core.py failed:", e)

if app is None:
    try:
        # Prefer import of loader-style core if present
        try:
            import importlib
            import server_core as _sc
            if getattr(_sc, "app", None) is not None:
                app = _sc.app
                for _n in ("PUBLIC_PATHS", "BASE_DIR", "DATA_DIR"):
                    if hasattr(_sc, _n):
                        globals()[_n] = getattr(_sc, _n)
                _boot_mode = "server_core.py (import)"
                print(f"[boot] Phase A: {_boot_mode} OK")
        except Exception as _ie:
            print("[boot] import server_core failed:", _ie)
    except Exception:
        pass

if app is None:
    try:
        _core = _materialize_core_from_b64()
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (from b64)")
    except Exception as e:
        raise RuntimeError(f"Phase A boot failed: {e}") from e

print(f"[boot] mode={_boot_mode}")

# Post-core patches via existing emergency split files if present
try:
    from pathlib import Path as _P
    _root = _P(__file__).resolve().parent
    _p0 = _root / "db" / "boot_after_0.py"
    _p1 = _root / "db" / "boot_after_1.py"
    if _p0.is_file() and _p1.is_file():
        _after = _p0.read_text(encoding="utf-8") + _p1.read_text(encoding="utf-8")
        exec(compile(_after, "db/boot_after_core.py", "exec"), globals())
    else:
        print("[boot] boot_after_0/1 missing — patches may be incomplete")
except Exception as _e:
    print("[boot] boot_after_core failed:", _e)
