"""Phase 2 JWT + Phase 3 student link/access — applied onto Flask app."""
from __future__ import annotations

from flask import jsonify, request

from db import student_access
from db.auth_tokens import issue_user_token, issue_admin_token, user_from_token, admin_from_token
from db import repo


def create_admin_token(admin: dict) -> str:
    return issue_admin_token(admin)


def create_user_token(user: dict) -> str:
    return issue_user_token(user)


def require_admin():
    return admin_from_token(request.headers.get("X-Admin-Token", ""))


def require_user():
    tok = (
        request.headers.get("X-User-Token")
        or request.headers.get("X-User-Token".lower())
        or ""
    )
    if not tok:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            tok = auth[7:].strip()
    return user_from_token(tok)


def register_routes(app, public_student, public_user, olympiad_window_status):
    @app.post("/api/student/link")
    def student_link():
        user = require_user()
        if not user:
            return jsonify({"error": "Аввал бо Google ворид шавед."}), 401
        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("studentId") or payload.get("id") or "").strip()
        if not student_id:
            return jsonify({"error": "Student ID лозим аст."}), 400
        linked = student_access.link_student_to_user(student_id, user["id"])
        if not linked:
            return jsonify({"error": "ID нодуруст ё аллакай пайваст."}), 400
        return jsonify({"ok": True, "student": public_student(linked)})

    @app.get("/api/student/me")
    def student_me():
        user = require_user()
        if not user:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        student = student_access.find_student_by_user_id(user["id"])
        return jsonify({
            "user": user,
            "student": public_student(student) if student else None,
            "linked": bool(student),
        })

    @app.get("/api/admin/olympiads/<olympiad_id>/participants")
    def admin_list_participants(olympiad_id: str):
        admin = require_admin()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        return jsonify({"participants": student_access.list_olympiad_participants(olympiad_id)})

    @app.post("/api/admin/olympiads/<olympiad_id>/participants")
    def admin_set_participants(olympiad_id: str):
        admin = require_admin()
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if not repo.find_olympiad(olympiad_id):
            return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
        payload = request.get_json(silent=True) or {}
        codes = payload.get("studentIds") or payload.get("ids") or []
        if not isinstance(codes, list):
            return jsonify({"error": "studentIds бояд рӯйхат бошад."}), 400
        parts = student_access.set_olympiad_participants(olympiad_id, codes)
        return jsonify({"participants": parts, "count": len(parts)})

    @app.post("/api/olympiads/<olympiad_id>/access")
    def olympiad_access(olympiad_id: str):
        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("studentId") or "").strip()
        if not student_id:
            return jsonify({"error": "studentId лозим аст."}), 400
        olympiad = repo.find_olympiad(olympiad_id)
        if not olympiad:
            return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
        window = olympiad_window_status(olympiad)
        if window != "open":
            return jsonify({"allowed": False, "reason": window, "windowStatus": window}), 403
        access = student_access.student_has_olympiad_access(olympiad_id, student_id)
        status = 200 if access.get("allowed") else 403
        body = {
            "allowed": access.get("allowed"),
            "reason": access.get("reason"),
            "windowStatus": window,
        }
        if access.get("student"):
            body["student"] = public_student(access["student"])
        return jsonify(body), status
