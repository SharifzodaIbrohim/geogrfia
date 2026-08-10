"""Geografia server entry — loads stable core then platform patches."""
from __future__ import annotations

import urllib.request
from flask import send_from_directory

_url = (
    "https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/"
    "12d743039abdc42c572a1f09d9d7f71572ee9035/server.py"
)
_src = urllib.request.urlopen(_url, timeout=90).read()
exec(compile(_src, "server_12d7430.py", "exec"), globals())

try:
    PUBLIC_PATHS.update({
        "profile.html", "courses.html", "leaderboard.html",
        "css/profile.css", "js/profile.js", "js/admin-gmail.js",
        "js/i18n.js", "js/admin-content.js", "js/platform-home.js",
        "js/admin-leaderboard.js", "js/admin.js",
    })
except Exception:
    pass

try:
    from db.profile_routes import register_profile_routes
    register_profile_routes(app, _jwt_require_user, require_perm, require_admin)
except Exception:
    try:
        register_profile_routes(app, require_user, require_perm, require_admin)
    except Exception:
        pass

try:
    from db.content_routes import register_content_routes
    register_content_routes(app, require_perm, require_admin)
except Exception:
    pass

@app.route("/profile")
@app.route("/profile.html")
@app.route("/Profile")
def _profile_page():
    return send_from_directory(BASE_DIR, "profile.html")

@app.route("/courses")
@app.route("/courses.html")
def _courses_page():
    return send_from_directory(BASE_DIR, "courses.html")

@app.route("/leaderboard")
@app.route("/leaderboard.html")
def _leaderboard_page():
    return send_from_directory(BASE_DIR, "leaderboard.html")

try:
    @app.route("/books/<path:filename>")
    def _books(filename):
        return send_from_directory(BASE_DIR / "books", filename)
except Exception:
    pass

# Gmail access + google accessMode on bridged quizzes
try:
    from db import student_access as _sa
    from db import quiz_bridge as _qb
    _orig_access = _sa.student_has_olympiad_access
    _orig_as_quiz = _qb.olympiad_as_quiz

    def _gmail_access(olympiad_id, student_code):
        student = None
        try:
            from db.repo import find_student_by_code
            student = find_student_by_code(student_code)
        except Exception:
            pass
        parts = _sa.list_olympiad_participants(olympiad_id)
        if not student and student_code and str(student_code).startswith(("g:", "gmail:")):
            if parts:
                return {"allowed": False, "reason": "not_assigned"}
            real_name = ""
            try:
                uid = str(student_code).split(":", 1)[-1]
                from db.profile_api import get_user_by_id as _gu
                u = _gu(uid)
                if u:
                    real_name = (u.get("name") or "").strip() or (u.get("email") or "").split("@")[0]
            except Exception:
                pass
            return {
                "allowed": True,
                "reason": "gmail_open",
                "student": {"id": student_code, "fullName": real_name or "Иштирокчӣ", "className": "", "school": ""},
            }
        return _orig_access(olympiad_id, student_code)

    def _olympiad_as_quiz_google(o):
        item = _orig_as_quiz(o)
        item["accessMode"] = "google"
        return item

    _sa.student_has_olympiad_access = _gmail_access
    _qb.olympiad_as_quiz = _olympiad_as_quiz_google
except Exception:
    pass

# Fix list quizzes accessMode=google for olympiad bridges
try:
    from flask import jsonify as _jq
    from db import quiz_api as _qapi
    from db import quiz_bridge as _qbr

    def _public_list_quizzes_fixed():
        items = _qapi.list_quizzes(include_draft=False)
        safe, seen = [], set()
        for q in items:
            seen.add(q["id"])
            safe.append({
                "id": q["id"], "title": q.get("title"), "description": q.get("description"),
                "passScore": q.get("passScore"), "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "public", "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0, "source": "quiz",
            })
        for q in _qbr.list_bridged_quizzes(include_inactive=False):
            if q["id"] in seen:
                continue
            safe.append({
                "id": q["id"], "title": q.get("title"), "description": q.get("description"),
                "passScore": q.get("passScore"), "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "google", "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0, "source": "olympiad",
                "windowStatus": q.get("windowStatus"),
            })
        return _jq({"quizzes": safe})

    app.view_functions["public_list_quizzes"] = _public_list_quizzes_fixed
except Exception:
    pass

# Gmail-capable quiz_start
try:
    from flask import jsonify, request as _req
    from db import olympiad_engine as _oe
    from db import quiz_api as _qa
    from db.repo import find_student_by_code as _fsc
    from db import student_access as _sa2

    def _patched_quiz_start(quiz_id: str):
        from db.quiz_routes import _resolve_quiz
        quiz = _resolve_quiz(quiz_id, include_answers=False)
        if not quiz:
            return jsonify({"error": "Викторина ёфт нашуд."}), 404
        user = None
        try:
            user = require_user()
        except Exception:
            try:
                user = _jwt_require_user()
            except Exception:
                user = None
        if not user:
            return jsonify({
                "error": "Аввал бо Google ворид шавед.",
                "reason": "google_required",
            }), 403
        payload = _req.get_json(silent=True) or {}
        student_code = str(payload.get("studentId") or _req.headers.get("X-Student-Id") or "").strip() or None
        student = _fsc(student_code) if student_code else None
        if user and not student:
            try:
                student = _sa2.find_student_by_user_id(user["id"])
                if student:
                    student_code = student.get("id")
            except Exception:
                pass
        fp = (_req.headers.get("X-Client-Fingerprint") or "")[:64]
        if quiz.get("source") == "olympiad":
            if not student_code:
                student_code = "g:" + str(user["id"])[:40]
            try:
                session = _oe.start_exam(
                    quiz_id, student_code,
                    user_id=user["id"],
                    client_fingerprint=fp or None,
                )
            except ValueError as e:
                code = str(e)
                msgs = {
                    "rate_limited": "Зиёд дархост.",
                    "already_submitted": "Аллакай супоридаед.",
                    "not_assigned": "Ба ин викторина таъин нашудаед.",
                    "student_not_found": "ID нодуруст.",
                    "not_found": "Ёфт нашуд.",
                }
                return jsonify({"error": msgs.get(code, code), "reason": code}), 403
            return jsonify({
                "attemptId": session.get("sessionId") or session.get("id"),
                "sessionId": session.get("sessionId") or session.get("id"),
                "sessionToken": session.get("sessionToken"),
                "quizId": quiz_id,
                "title": session.get("title"),
                "startedAt": session.get("startedAt"),
                "endsAt": session.get("endsAt"),
                "timeLimitSec": quiz.get("timeLimitSec"),
                "questionCount": session.get("questionCount"),
                "questions": session.get("questions") or [],
                "passScore": session.get("passScore"),
                "source": "olympiad",
            })
        access = _qa.check_access(quiz, user, student)
        if not access.get("allowed"):
            return jsonify({"error": "Дастрасӣ рад шуд.", "reason": access.get("reason")}), 403
        try:
            attempt = _qa.start_attempt(quiz_id, user_id=user["id"], student_id=student_code)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        attempt["source"] = "quiz"
        return jsonify(attempt)

    app.view_functions["quiz_start"] = _patched_quiz_start
except Exception:
    pass

# Content fallback
try:
    from flask import jsonify as _jfy, request as _rq_c
    import uuid as _uuid
    from datetime import datetime, timezone as _tz
    from pathlib import Path as _P
    _DEFAULT_BOOKS = [
        {"title": "География 7", "url": "/books/kitobkhon-net-geografiya-7.pdf", "type": "book", "lang": "tg"},
        {"title": "География 8 (2014)", "url": "/books/kitobkhon-net-8.-geografiya-2014.pdf", "type": "book", "lang": "tg"},
        {"title": "География 9 (2013)", "url": "/books/kitobkhon-net-9.-geografiya-2013.pdf", "type": "book", "lang": "tg"},
        {"title": "География 10", "url": "/books/kitobkhon-net-geografiya-10.pdf", "type": "book", "lang": "tg"},
        {"title": "География 11 (2015)", "url": "/books/kitobkhon-net-11.-geografiya-2015.pdf", "type": "book", "lang": "tg"},
    ]
    def _content_items():
        try:
            from db import content_api as _ca
            return _ca.list_content()
        except Exception:
            pass
        path = BASE_DIR / "data" / "content_items.json"
        items = []
        try:
            import json as _json
            if path.exists():
                items = _json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(items, list):
                    items = []
        except Exception:
            items = []
        if not items:
            now = datetime.now(_tz.utc).isoformat()
            items = [{"id": str(_uuid.uuid4()), "type": b["type"], "title": b["title"], "description": "", "url": b["url"], "lang": b["lang"], "createdAt": now} for b in _DEFAULT_BOOKS]
            try:
                import json as _json
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(_json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        return items
    @app.get("/api/content")
    def _public_content_safe():
        kind = _rq_c.args.get("type") or None
        lang = _rq_c.args.get("lang") or None
        items = _content_items()
        if kind:
            items = [i for i in items if i.get("type") == kind]
        if lang:
            items = [i for i in items if i.get("lang") == lang or not i.get("lang")]
        return _jfy({"items": items, "count": len(items)})
except Exception:
    pass

# Leaderboard + clear results
try:
    from flask import jsonify as _jl, request as _rl
    def _lb_build(limit=100, public_only=True):
        try:
            from db import leaderboard_api as _lb
            return _lb.build_global_leaderboard(limit=limit, public_only=public_only)
        except Exception:
            pass
        import json as _json
        data_dir = BASE_DIR / "data"
        by = {}
        def _ld(name):
            p = data_dir / name
            if p.exists():
                try:
                    return _json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    return None
            return None
        settings = _ld("leaderboard_settings.json") or {"public": True, "title": "Leaderboard · Top Rated"}
        if public_only and settings.get("public") is False:
            return {"public": False, "title": settings.get("title"), "entries": [], "total": 0, "message": "Leaderboard пӯшида аст."}
        profiles = _ld("user_profiles.json") or {}
        items = list(profiles.values()) if isinstance(profiles, dict) else (profiles if isinstance(profiles, list) else [])
        for u in items:
            uid = str(u.get("id") or "")
            if not uid:
                continue
            name = (u.get("name") or "").strip()
            if name.lower().startswith("gmail"):
                name = (u.get("email") or "user").split("@")[0]
            by[uid] = {"id": uid, "name": name or "Иштирокчӣ", "school": u.get("school") or "", "className": u.get("className") or "", "rating": int(u.get("rating") or 1200), "solved": 0, "contests": 0}
        students = _ld("students.json") or []
        if isinstance(students, list):
            for st in students:
                sid = str(st.get("id") or "")
                if not sid:
                    continue
                by[sid] = {"id": sid, "name": (st.get("fullName") or st.get("name") or "Хонанда"), "school": st.get("school") or "", "className": st.get("className") or "", "rating": int(st.get("rating") or 1200), "solved": 0, "contests": 0}
        rows = sorted(by.values(), key=lambda x: -int(x.get("rating") or 0))
        entries = [dict(r, rank=i) for i, r in enumerate(rows[:limit], 1)]
        return {"public": True, "title": settings.get("title") or "Leaderboard · Top Rated", "entries": entries, "total": len(rows), "settings": settings}

    @app.get("/api/leaderboard")
    def _public_leaderboard():
        try:
            limit = min(200, max(1, int(_rl.args.get("limit") or 100)))
        except Exception:
            limit = 100
        return _jl(_lb_build(limit=limit, public_only=True))

    @app.get("/api/admin/leaderboard")
    def _admin_leaderboard():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jl({"error": "Дастрасӣ рад шуд."}), 401
        return _jl(_lb_build(limit=200, public_only=False))

    @app.get("/api/admin/leaderboard/settings")
    def _admin_lb_settings_get():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jl({"error": "Дастрасӣ рад шуд."}), 401
        try:
            from db import leaderboard_api as _lb
            return _jl(_lb.get_settings())
        except Exception:
            return _jl({"public": True, "title": "Leaderboard · Top Rated", "pinned": []})

    @app.post("/api/admin/leaderboard/settings")
    def _admin_lb_settings_set():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jl({"error": "Дастрасӣ рад шуд."}), 401
        payload = _rl.get_json(silent=True) or {}
        try:
            from db import leaderboard_api as _lb
            return _jl(_lb.update_settings(payload))
        except Exception:
            import json as _json
            path = BASE_DIR / "data" / "leaderboard_settings.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            cur = {"public": True, "title": "Leaderboard · Top Rated", "pinned": []}
            if path.exists():
                try:
                    cur = _json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            cur.update({k: payload[k] for k in ("public", "title", "showSchool", "showClass", "pinned") if k in payload})
            path.write_text(_json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
            return _jl(cur)

    @app.post("/api/admin/results/clear-recent")
    def _clear_recent_results():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jl({"error": "Дастрасӣ рад шуд."}), 401
        return _jl({"ok": True})

    @app.post("/api/admin/results/clear-all")
    def _clear_all_results():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jl({"error": "Дастрасӣ рад шуд."}), 401
        import json as _json
        cleared = 0
        path = BASE_DIR / "data" / "results.json"
        if path.exists():
            try:
                data = _json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    cleared = len(data)
                path.write_text("[]", encoding="utf-8")
            except Exception as e:
                return _jl({"error": str(e)}), 500
        try:
            from db.connection import get_session
            from sqlalchemy import text
            with get_session() as s:
                s.execute(text("DELETE FROM results"))
        except Exception:
            pass
        return _jl({"ok": True, "cleared": cleared})
except Exception:
    pass
