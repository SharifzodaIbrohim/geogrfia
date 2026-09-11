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

_EXTRA_PUBLIC = {
    "index.html", "admin.html", "student.html", "profile.html", "quiz.html",
    "courses.html", "leaderboard.html", "countries.html", "css.css",
    "css/admin.css", "css/student.css", "css/quiz.css", "css/platform.css", "css/profile.css",
    "js.js", "js/i18n.js", "js/platform-home.js", "js/quiz-platform.js", "js/profile.js",
    "js/admin.js", "js/admin-session.js", "js/admin-fixes.js", "js/admin-gmail.js",
    "js/admin-content.js", "js/admin-leaderboard.js", "js/admin-olympiad.js",
    "js/admin-students-reg.js", "js/admin-davotnoma-print.js", "js/admin-rbac-ui.js",
    "js/admin-audit.js", "js/admin-export.js", "js/admin-results-review.js",
    "js/admin-results-click-fix.js", "js/student.js", "js/student-confirm.js",
    "favicon.svg", "favicon.png", "robots.txt", "sitemap.xml", "og-default.png",
}
for _i in range(24):
    _EXTRA_PUBLIC.add(f"_asr_x{_i}.txt")
for _i in range(4):
    _EXTRA_PUBLIC.add(f"_st_b64_{_i}.txt")
    _EXTRA_PUBLIC.add(f"_st_p{_i}.txt")
for _i in range(6):
    _EXTRA_PUBLIC.add(f"_ao_b64_{_i}.txt")
for _i in range(10):
    _EXTRA_PUBLIC.add(f"js/_sh{_i}.txt")
    _EXTRA_PUBLIC.add(f"_sh{_i}.txt")
for _i in range(10):
    _EXTRA_PUBLIC.add(f"js/_i18{_i}.txt")
    _EXTRA_PUBLIC.add(f"_i18{_i}.txt")
for _i in range(9):
    _EXTRA_PUBLIC.add(f"js/_aj{_i}.txt")
    _EXTRA_PUBLIC.add(f"_aj{_i}.txt")
try:
    if isinstance(globals().get("PUBLIC_PATHS"), set):
        PUBLIC_PATHS |= _EXTRA_PUBLIC
    elif isinstance(globals().get("PUBLIC_PATHS"), (list, tuple)):
        PUBLIC_PATHS = list(PUBLIC_PATHS) + sorted(_EXTRA_PUBLIC)
except Exception as e:
    print("[boot] PUBLIC_PATHS merge skipped:", e)

# Boot patches (order matters)
try:
    from db.patch_student_portal import install as _isp
    _isp(app)
except Exception as e:
    print("[boot] patch_student_portal failed:", e)

try:
    from db.patch_admin_create_role import install as _pacr
    _pacr(app)
except Exception as e:
    print("[boot] patch_admin_create_role failed:", e)

try:
    from db.patch_admin_auth_bearer import install as _paab
    _paab(app)
except Exception as e:
    print("[boot] patch_admin_auth_bearer failed:", e)

try:
    from db.patch_olympiad_builder import install as _pob
    _pob(app)
except Exception as e:
    print("[boot] patch_olympiad_builder failed:", e)

try:
    from db.patch_answers_durable import install as _pad
    _pad(app)
except Exception as e:
    print("[boot] patch_answers_durable failed:", e)

try:
    from db.patch_attempt_review import install as _par
    _par(app)
except Exception as e:
    print("[boot] patch_attempt_review failed:", e)

try:
    from db.patch_results_score_fix import install as _prsf
    _prsf(app)
except Exception as e:
    print("[boot] patch_results_score_fix failed:", e)
