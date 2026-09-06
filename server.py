"""Geografia entry — Phase A: plain server_core.py preferred (no network at boot)."""
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
    "js/admin-students-reg-body-a.js", "js/admin-students-reg-body-b.js",
    "js/_asr_x0.txt", "js/_asr_x1.txt", "js/_asr_x2.txt", "js/_asr_x3.txt",
    "js/_asr_x4.txt", "js/_asr_x5.txt", "js/_asr_x6.txt", "js/_asr_x7.txt",
    "js/_asr_x8.txt", "js/_asr_x9.txt", "js/_asr_x10.txt", "js/_asr_x11.txt",
    "js/_asr_x12.txt", "js/_asr_x13.txt", "js/_asr_x14.txt", "js/_asr_x15.txt",
    "js/_asr_x16.txt", "js/_asr_x17.txt", "js/_asr_x18.txt", "js/_asr_x19.txt",
    "js/_asr_x20.txt", "js/_asr_x21.txt", "js/_asr_x22.txt", "js/_asr_x23.txt",
    "_asr_x0.txt", "_asr_x1.txt", "_asr_x2.txt", "_asr_x3.txt",
    "_asr_x4.txt", "_asr_x5.txt", "_asr_x6.txt", "_asr_x7.txt",
    "_asr_x8.txt", "_asr_x9.txt", "_asr_x10.txt", "_asr_x11.txt",
    "_asr_x12.txt", "_asr_x13.txt", "_asr_x14.txt", "_asr_x15.txt",
    "_asr_x16.txt", "_asr_x17.txt", "_asr_x18.txt", "_asr_x19.txt",
    "_asr_x20.txt", "_asr_x21.txt", "_asr_x22.txt", "_asr_x23.txt",
    "Аз_тарафи_чап.jpg", "Аз_тарафи_рост.jpg",
    "robots.txt", "sitemap.xml", "favicon.svg", "favicon.ico",
}

try:
    g = globals()
    if "PUBLIC_PATHS" in g and isinstance(g["PUBLIC_PATHS"], set):
        g["PUBLIC_PATHS"].update(_EXTRA_PUBLIC)
        print("[boot] PUBLIC_PATHS set += extras (%d)" % len(g["PUBLIC_PATHS"]))
    if app is not None and hasattr(app, "config"):
        existing = set(app.config.get("PUBLIC_PATHS") or [])
        app.config["PUBLIC_PATHS"] = existing | _EXTRA_PUBLIC
        print("[boot] PUBLIC_PATHS: current static set OK")
except Exception as e:
    print("[boot] PUBLIC_PATHS merge failed:", e)


def _boot_patch(name: str, *modules: str) -> None:
    last = None
    for mod in modules:
        try:
            m = __import__(mod, fromlist=["install"])
            install = getattr(m, "install", None)
            if install is None:
                continue
            try:
                install(app)
            except TypeError:
                install()
            print(f"[boot] {name} via {mod}")
            return
        except Exception as e:
            last = e
    if last is not None:
        print(f"[boot] {name} failed:", last)


_boot_patch("one_attempt", "one_attempt", "db.one_attempt")
_boot_patch("patch_submit_p112", "patch_submit_p112", "db.patch_submit_p112")
_boot_patch("patch_student_portal", "patch_student_portal", "db.patch_student_portal")
_boot_patch("patch_admin_students", "patch_admin_students", "db.patch_admin_students")
_boot_patch("patch_names", "patch_names", "db.patch_names")
_boot_patch("patch_students_profile", "patch_students_profile", "db.patch_students_profile")
_boot_patch("patch_olympiad_builder", "patch_olympiad_builder", "db.patch_olympiad_builder")
_boot_patch("patch_olympiad_questions_pg", "patch_olympiad_questions_pg", "db.patch_olympiad_questions_pg")
_boot_patch("patch_ui_batch", "patch_ui_batch", "db.patch_ui_batch")
_boot_patch("patch_score_text", "patch_score_text", "db.patch_score_text")
_boot_patch("patch_clear_recent", "patch_clear_recent", "db.patch_clear_recent")
_boot_patch("force_olympiad_routes", "force_olympiad_routes", "db.force_olympiad_routes")
_boot_patch("patch_attempts_kind", "patch_attempts_kind", "db.patch_attempts_kind")
_boot_patch("patch_duration", "patch_duration", "db.patch_duration")
_boot_patch("patch_duration_api", "patch_duration_api", "db.patch_duration_api")
_boot_patch("patch_attempt_review", "patch_attempt_review", "db.patch_attempt_review")
_boot_patch("patch_persist_answers", "patch_persist_answers", "db.patch_persist_answers")
_boot_patch("patch_answers_durable", "db.patch_answers_durable", "patch_answers_durable")
_boot_patch("patch_monitor_durable", "db.patch_monitor_durable", "patch_monitor_durable")
_boot_patch("patch_review_text_fix", "patch_review_text_fix", "db.patch_review_text_fix")
_boot_patch("patch_admin_export", "patch_admin_export", "db.patch_admin_export")
_boot_patch("patch_google_login_detail", "db.patch_google_login_detail", "patch_google_login_detail")
_boot_patch("patch_seo_cache", "db.patch_seo_cache", "patch_seo_cache")


def _install_safety_net() -> None:
    from flask import request, jsonify
    if "student_login" in app.view_functions:
        _orig = app.view_functions["student_login"]
        def student_login_safe():
            data = request.get_json(silent=True) or {}
            sid = data.get("id") or data.get("studentId") or data.get("code")
            if sid and not data.get("id"):
                try:
                    request._cached_json = ({**data, "id": str(sid).strip()}, {**data, "id": str(sid).strip()})
                except Exception:
                    pass
            return _orig()
        app.view_functions["student_login"] = student_login_safe
        print("[boot] safety-net: student_login id|studentId|code")

    def _google_login_safe():
        try:
            from db.google_auth import (
                google_configured,
                GOOGLE_CLIENT_ID,
                verify_google_id_token,
            )
            try:
                from db.google_auth import last_verify_error
            except Exception:
                def last_verify_error():
                    return None
            try:
                from db import repo as _repo
            except Exception:
                import sys
                _repo = sys.modules.get("db.repo") or sys.modules.get("repo") or globals().get("repo")
                if _repo is None:
                    raise ModuleNotFoundError("repo module not found (db.repo)")

            if not google_configured():
                return jsonify({"error": "Google OAuth танзим нашудааст.", "detail": "no_client_id"}), 503

            payload = request.get_json(silent=True) or {}
            id_token = str(
                payload.get("idToken") or payload.get("credential") or payload.get("token") or ""
            ).strip()
            if not id_token:
                return jsonify({"error": "idToken лозим аст.", "detail": "missing_token"}), 400

            info = verify_google_id_token(id_token)
            if not info:
                err = None
                try:
                    err = last_verify_error()
                except Exception:
                    err = None
                return jsonify({
                    "error": "Google token нодуруст аст.",
                    "detail": err or "verify_failed",
                    "clientIdPrefix": (GOOGLE_CLIENT_ID[:24] + "\u2026") if GOOGLE_CLIENT_ID else None,
                }), 401

            try:
                user = _repo.upsert_google_user(
                    google_id=info["sub"],
                    email=info["email"],
                    name=info["name"],
                    avatar=info.get("picture"),
                )
            except Exception as e:
                detail = f"{type(e).__name__}: {e}"
                try:
                    from sqlalchemy import text as _text
                    from db.connection import get_session
                    import uuid as _uuid
                    email = (info["email"] or "").lower().strip()
                    with get_session() as s:
                        r = s.execute(
                            _text("SELECT id::text FROM users WHERE google_id = :g OR lower(email) = :e"),
                            {"g": info["sub"], "e": email},
                        ).first()
                        if r:
                            uid = str(r[0])
                            try:
                                s.execute(
                                    _text("UPDATE users SET google_id=:g, email=:e, name=:n WHERE id::text=:id"),
                                    {"g": info["sub"], "e": email, "n": info["name"], "id": uid},
                                )
                            except Exception:
                                pass
                        else:
                            uid = str(_uuid.uuid4())
                            s.execute(
                                _text("INSERT INTO users (id, google_id, email, name) VALUES (:id,:g,:e,:n)"),
                                {"id": uid, "g": info["sub"], "e": email, "n": info["name"]},
                            )
                        user = {
                            "id": uid,
                            "email": email,
                            "name": info["name"],
                            "avatar": info.get("picture"),
                            "googleId": info["sub"],
                        }
                except Exception as e2:
                    return jsonify({
                        "error": "Сабти корбар ноком шуд.",
                        "detail": detail + " | fallback: " + f"{type(e2).__name__}: {e2}",
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
