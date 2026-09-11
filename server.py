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
    "js/admin-students-reg.js", "js/admin-students-reg-body.js",
    "js/admin-davotnoma-print.js", "js/admin-rbac-ui.js", "js/admin-audit.js", "js/student.js",
    "js/admin-results-review.js",
    "js/admin-results-click-fix.js",
    "js/admin-export.js",
    "js/_rrgz_0.txt", "js/_rrgz_1.txt", "js/_rrgz_2.txt", "js/_rrgz_3.txt",
    "js/_asr_s0.txt", "js/_asr_s1.txt", "js/_asr_s2.txt", "js/_asr_s3.txt",
    "js/_asr_s4.txt", "js/_asr_s5.txt", "js/_asr_s6.txt", "js/_asr_s7.txt",
    "js/_asr_p0.txt", "js/_asr_p1.txt", "js/_asr_p2.txt", "js/_asr_p3.txt",
    "js/_asr_body_a.txt", "js/_asr_body_b.txt",
}

for _i in range(24):
    _EXTRA_PUBLIC.add(f"_asr_x{_i}.txt")
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
    from server_public_paths_note import EXTRA as _NOTE_EXTRA
    _EXTRA_PUBLIC |= set(_NOTE_EXTRA)
except Exception:
    pass

try:
    if isinstance(globals().get("PUBLIC_PATHS"), set):
        PUBLIC_PATHS |= _EXTRA_PUBLIC
    elif isinstance(globals().get("PUBLIC_PATHS"), (list, tuple)):
        PUBLIC_PATHS = list(PUBLIC_PATHS) + sorted(_EXTRA_PUBLIC)
except Exception as e:
    print("[boot] PUBLIC_PATHS merge skipped:", e)


def _install_safety_net():
    from flask import jsonify, request

    def _google_login_safe():
        try:
            data = request.get_json(silent=True) or {}
            id_token = (
                data.get("idToken")
                or data.get("credential")
                or data.get("id_token")
                or ""
            )
            if not id_token:
                return jsonify({"error": "idToken лозим аст.", "detail": "missing_id_token"}), 400
            try:
                from db.google_auth import verify_google_id_token
                user = verify_google_id_token(id_token)
            except Exception as e:
                try:
                    from db.phase23_hooks import verify_google_token as verify_tok
                    user = verify_tok(id_token)
                except Exception as e2:
                    return jsonify({
                        "error": "Google token нодуруст.",
                        "detail": f"{type(e).__name__}: {e} | {type(e2).__name__}: {e2}",
                    }), 500

            if not user or not user.get("id"):
                return jsonify({"error": "Корбар холӣ.", "detail": "empty_user"}), 500

            try:
                from db.auth_tokens import issue_user_token
                token = issue_user_token(user)
            except Exception as e:
                try:
                    from db.phase23_hooks import create_user_token as create_tok
                    token = create_tok(user)
                except Exception as e2:
                    return jsonify({
                        "error": "Сохтани session ноком шуд.",
                        "detail": f"{type(e).__name__}: {e} | {type(e2).__name__}: {e2}",
                    }), 500
            if not isinstance(token, str):
                token = token.decode("utf-8") if isinstance(token, (bytes, bytearray)) else str(token)
            if token.count(".") != 2:
                return jsonify({
                    "error": "Token формати нодуруст.",
                    "detail": f"expected JWT, got len={len(token)} dots={token.count('.')}",
                }), 500

            if not token:
                return jsonify({"error": "Token холӣ.", "detail": "empty_token"}), 500

            pub = {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "avatar": user.get("avatar") or user.get("avatar_url"),
                "googleId": user.get("googleId") or user.get("google_id"),
            }
            return jsonify({"user": pub, "token": token, "ok": True})
        except Exception as e:
            return jsonify({
                "error": "Хатои дохилии Google login.",
                "detail": f"{type(e).__name__}: {e}",
            }), 500

    bound = 0
    for rule in list(app.url_map.iter_rules()):
        if str(rule.rule).rstrip("/") == "/api/auth/google":
            app.view_functions[rule.endpoint] = _google_login_safe
            bound += 1
            print(f"[boot] safety-net: rebound {rule.endpoint} -> google_login_safe")
    if "google_login" in app.view_functions:
        app.view_functions["google_login"] = _google_login_safe
        bound += 1
    print(f"[boot] safety-net: google_login bound={bound}")
    print("[boot] safety-net OK")


try:
    _install_safety_net()
except Exception as e:
    print("[boot] safety-net failed:", e)

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

# --- Names on results + durable monitor ---
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


# --- Score by question text (shuffle-safe) — MUST run before answers_durable ---
try:
    from db.patch_score_text import install as _install_score_text
    _install_score_text(app)
    print("[boot] patch_score_text installed")
except Exception as e:
    print("[boot] patch_score_text failed:", e)

# --- Durable answers on submit (answers_json + attempt_answers) ---
try:
    from db.patch_answers_durable import install as _install_answers_durable
    _install_answers_durable(app)
except Exception as e:
    print("[boot] patch_answers_durable failed:", e)

# --- Attempt review (admin Results click) ---
try:
    from db.patch_attempt_review import install as _install_attempt_review
    _install_attempt_review(app)
except Exception as e:
    print("[boot] patch_attempt_review failed:", e)

# --- clear-recent: real DB delete of last finished attempts ---
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
