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
        _core = _materialize_core_from_b64()
        _exec_src(_core.read_text(encoding="utf-8"), "server_core.py (from b64)")
    except Exception as e:
        raise RuntimeError(f"Phase A boot failed: {e}") from e

print(f"[boot] mode={_boot_mode}")

# Boot patches are installed by server_core; additional safety hooks below.
try:
    from db.patch_student_portal import install as _install_student_portal
    _install_student_portal(app)
except Exception as e:
    print("[boot] patch_student_portal failed:", e)
    try:
        from db.install_student_portal import install as _isp
        _isp(app)
        print("[boot] install_student_portal fallback OK")
    except Exception as e2:
        print("[boot] install_student_portal also failed:", e2)

try:
    from db.patch_admin_create_role import install as _install_admin_create_role
    _install_admin_create_role(app)
except Exception as e:
    print("[boot] patch_admin_create_role failed:", e)

try:
    from db.patch_admin_auth_bearer import install as _install_admin_auth_bearer
    _install_admin_auth_bearer(app)
except Exception as e:
    print("[boot] patch_admin_auth_bearer failed:", e)

try:
    from db.patch_names import install as _install_patch_names
    _install_patch_names(app)
except Exception as e:
    print("[boot] patch_names failed:", e)

try:
    from db.patch_monitor_durable import install as _install_monitor_durable
    _install_monitor_durable(app)
except Exception as e:
    print("[boot] patch_monitor_durable failed:", e)

try:
    from db.patch_score_text import install as _install_score_text
    _install_score_text(app)
    print("[boot] patch_score_text installed")
except Exception as e:
    print("[boot] patch_score_text failed:", e)

try:
    from db.patch_answers_durable import install as _install_answers_durable
    _install_answers_durable(app)
except Exception as e:
    print("[boot] patch_answers_durable failed:", e)

try:
    from db.patch_attempt_review import install as _install_attempt_review
    _install_attempt_review(app)
except Exception as e:
    print("[boot] patch_attempt_review failed:", e)

try:
    from db.patch_results_score_fix import install as _install_results_score_fix
    _install_results_score_fix(app)
except Exception as e:
    print("[boot] patch_results_score_fix failed:", e)

try:
    from db.patch_clear_recent import install as _install_clear_recent
    _install_clear_recent(app)
except Exception as e:
    print("[boot] patch_clear_recent failed:", e)

try:
    from db.bootstrap_admin import install_bootstrap
    install_bootstrap()
except Exception as e:
    print("[boot] bootstrap_admin failed:", e)
