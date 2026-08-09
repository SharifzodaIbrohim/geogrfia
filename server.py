from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from db.connection import health_check as db_health_check
from db import repo
from db.google_auth import google_configured, GOOGLE_CLIENT_ID, verify_google_id_token

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
ADMINS_FILE = DATA_DIR / "admins.json"
STUDENTS_FILE = DATA_DIR / "students.json"
OLYMPIADS_FILE = DATA_DIR / "olympiads.json"
RESULTS_FILE = DATA_DIR / "results.json"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LOCK = threading.Lock()

PUBLIC_PATHS = {
    "index.html",
    "admin.html",
    "student.html",
    "css/style.css",
    "css/admin.css",
    "js/app.js",
    "js/admin.js",
    "js/student.js",
    "data/countries.json",
    "data/countries-full.json",
    "data/country-names-tg.json",
    "books/kitobkhon-net-geografiya-7.pdf",
    "books/kitobkhon-net-8.-geografiya-2014.pdf",
    "books/kitobkhon-net-9.-geografiya-2013.pdf",
    "books/kitobkhon-net-geografiya-10.pdf",
    "books/kitobkhon-net-11.-geografiya-2015.pdf",
}

app = Flask(__name__, static_folder=None)
app.config["JSON_AS_ASCII"] = False


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-Admin-Token, X-Student-Id, X-User-Token"
    )
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    if request.method == "OPTIONS":
        response.status_code = 204
    return response


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(value):
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def ensure_json_file(path: Path, default="[]") -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not path.exists():
        path.write_text(default, encoding="utf-8")


def load_json(path: Path) -> list | dict:
    ensure_json_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    return data


def save_json(path: Path, data) -> None:
    ensure_json_file(path)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=DATA_DIR, delete=False, prefix="tmp-", suffix=".tmp"
    ) as temp_file:
        temp_file.write(payload)
        temp_name = temp_file.name
    Path(temp_name).replace(path)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120_000,
    ).hex()
    return salt, password_hash


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    if not salt or not stored_hash:
        return False
    _, password_hash = hash_password(password, salt)
    return secrets.compare_digest(password_hash, stored_hash)


def generate_long_id() -> str:
    existing = repo.student_codes_set()
    for _ in range(50):
        num = secrets.randbelow(9 * 10**18) + 10**18
        sid = str(num)
        if sid not in existing:
            return sid
    return str(uuid.uuid4().int)[:19]


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user.get("name"),
        "email": user.get("email"),
        "avatar": user.get("avatar") or user.get("avatar_url"),
        "createdAt": user.get("createdAt"),
    }


def public_student(s: dict) -> dict:
    return {
        "id": s["id"],
        "fullName": s["fullName"],
        "className": s["className"],
        "school": s["school"],
        "createdAt": s.get("createdAt"),
        "createdBy": s.get("createdBy"),
    }


def public_admin(a: dict) -> dict:
    return {
        "id": a["id"],
        "login": a["login"],
        "name": a.get("name", a["login"]),
        "createdAt": a.get("createdAt"),
        "createdBy": a.get("createdBy"),
    }


def olympiad_window_status(o: dict) -> str:
    if not o.get("isActive"):
        return "inactive"
    now = datetime.now(timezone.utc)
    start = parse_dt(o.get("startTime"))
    end = parse_dt(o.get("endTime"))
    if start and now < start:
        return "not_started"
    if end and now > end:
        return "ended"
    return "open"


def is_olympiad_open(o: dict) -> bool:
    return olympiad_window_status(o) == "open"


def public_olympiad(o: dict, include_answers: bool = False) -> dict:
    questions = []
    for q in o.get("questions") or []:
        item = {
            "id": q["id"],
            "text": q["text"],
            "options": q.get("options") or [],
        }
        if include_answers:
            item["answer"] = q.get("answer")
        questions.append(item)
    window = olympiad_window_status(o)
    return {
        "id": o["id"],
        "title": o["title"],
        "type": o.get("type", "olympiad"),
        "passScore": o.get("passScore", 70),
        "isActive": bool(o.get("isActive")),
        "startTime": o.get("startTime"),
        "endTime": o.get("endTime"),
        "windowStatus": window,
        "isOpen": window == "open",
        "questions": questions,
        "questionCount": len(questions),
        "createdAt": o.get("createdAt"),
        "createdBy": o.get("createdBy"),
    }


ADMIN_TOKENS: dict[str, dict] = {}
USER_TOKENS: dict[str, dict] = {}


def create_admin_token(admin: dict) -> str:
    token = secrets.token_hex(24)
    ADMIN_TOKENS[token] = {
        "id": admin["id"],
        "login": admin["login"],
        "name": admin.get("name", admin["login"]),
    }
    return token


def create_user_token(user: dict) -> str:
    token = secrets.token_hex(24)
    USER_TOKENS[token] = public_user(user)
    return token


def require_admin():
    token = request.headers.get("X-Admin-Token", "")
    return ADMIN_TOKENS.get(token)


def require_user():
    token = request.headers.get("X-User-Token", "")
    return USER_TOKENS.get(token)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/admin")
@app.route("/admin.html")
def admin_page():
    return send_from_directory(BASE_DIR, "admin.html")


@app.route("/student")
@app.route("/student.html")
def student_page():
    return send_from_directory(BASE_DIR, "student.html")


@app.get("/api/health")
def api_health():
    h = db_health_check()
    return jsonify({
        "ok": True,
        "app": "geografia",
        "dataBackend": repo.backend_name(),
        "database": h,
        "googleAuth": google_configured(),
    })


# ---------- Legacy email auth (still JSON/PG via repo users) ----------

@app.post("/api/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if len(name) < 2:
        return jsonify({"error": "Ном бояд камаш 2 ҳарф бошад."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Email дуруст нест."}), 400
    if len(password) < 6:
        return jsonify({"error": "Парол бояд камаш 6 рамз бошад."}), 400

    if repo.find_user_by_email(email):
        return jsonify({"error": "Ин email аллакай сабт шудааст."}), 409

    salt, password_hash = hash_password(password)
    with LOCK:
        users = load_json(USERS_FILE)
        if not isinstance(users, list):
            users = []
        user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "salt": salt,
            "passwordHash": password_hash,
            "createdAt": utc_now(),
        }
        users.append(user)
        save_json(USERS_FILE, users)
    return jsonify({"user": public_user(user)}), 201


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    user = repo.find_user_by_email(email)
    if not user:
        users = load_json(USERS_FILE)
        user = next((item for item in users if item.get("email") == email), None)
    if not user or not verify_password(password, user.get("salt", ""), user.get("passwordHash", "")):
        return jsonify({"error": "Email ё парол нодуруст аст."}), 401

    token = create_user_token(user)
    return jsonify({"user": public_user(user), "token": token})


# ---------- Phase 2: Google Auth ----------

@app.get("/api/auth/google/status")
def google_status():
    return jsonify({
        "configured": google_configured(),
        "clientId": GOOGLE_CLIENT_ID if google_configured() else None,
    })


@app.post("/api/auth/google")
def google_login():
    if not google_configured():
        return jsonify({
            "error": "Google OAuth ҳоло танзим нашудааст. GOOGLE_CLIENT_ID-ро гузоред.",
        }), 503

    payload = request.get_json(silent=True) or {}
    id_token = str(payload.get("idToken") or payload.get("credential") or "").strip()
    if not id_token:
        return jsonify({"error": "idToken лозим аст."}), 400

    info = verify_google_id_token(id_token)
    if not info:
        return jsonify({"error": "Google token нодуруст аст."}), 401

    user = repo.upsert_google_user(
        google_id=info["sub"],
        email=info["email"],
        name=info["name"],
        avatar=info.get("picture"),
    )
    token = create_user_token(user)
    return jsonify({"user": public_user(user), "token": token})


@app.get("/api/auth/me")
def auth_me():
    user = require_user()
    if not user:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({"user": user})


# ---------- Admin auth ----------

@app.post("/api/admin/login")
def admin_login():
    payload = request.get_json(silent=True) or {}
    login_name = str(payload.get("login", "")).strip()
    password = str(payload.get("password", ""))

    admin = repo.find_admin_by_login(login_name)
    if not admin or not verify_password(password, admin.get("salt", ""), admin.get("passwordHash", "")):
        return jsonify({"error": "Логин ё парол нодуруст аст."}), 401

    token = create_admin_token(admin)
    return jsonify({
        "token": token,
        "admin": public_admin(admin),
        "backend": repo.backend_name(),
    })


@app.get("/api/admin/me")
def admin_me():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({"admin": admin, "backend": repo.backend_name()})


# ---------- Admins management ----------

@app.get("/api/admin/admins")
def admin_list_admins():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({"admins": [public_admin(a) for a in repo.list_admins()]})


@app.post("/api/admin/admins")
def admin_create_admin():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    payload = request.get_json(silent=True) or {}
    login_name = str(payload.get("login", "")).strip()
    name = str(payload.get("name", "")).strip() or login_name
    password = str(payload.get("password", ""))

    if len(login_name) < 3:
        return jsonify({"error": "Логин бояд камаш 3 рамз бошад."}), 400
    if len(password) < 6:
        return jsonify({"error": "Парол бояд камаш 6 рамз бошад."}), 400
    if repo.find_admin_by_login(login_name):
        return jsonify({"error": "Ин логин аллакай вуҷуд дорад."}), 409

    salt, password_hash = hash_password(password)
    new_admin = repo.create_admin(login_name, name, salt, password_hash, admin["login"])
    return jsonify({"admin": public_admin(new_admin)}), 201


@app.delete("/api/admin/admins/<admin_id>")
def admin_delete_admin(admin_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin.get("id") == admin_id:
        return jsonify({"error": "Шумо наметавонед худро нест кунед."}), 400
    if repo.count_admins() <= 1:
        return jsonify({"error": "Наметавон охирин админро нест кард."}), 400
    if not repo.delete_admin(admin_id):
        return jsonify({"error": "Админ ёфт нашуд."}), 404
    return jsonify({"ok": True})


# ---------- Students ----------

@app.get("/api/admin/students")
def admin_list_students():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({"students": [public_student(s) for s in repo.list_students()]})


@app.get("/api/admin/students/export")
def admin_export_students():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    students = repo.list_students()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Ному насаб", "Синф", "Мактаб", "Сохтааст", "Сана"])
    for s in students:
        writer.writerow([
            s.get("id", ""),
            s.get("fullName", ""),
            s.get("className", ""),
            s.get("school", ""),
            s.get("createdBy", ""),
            (s.get("createdAt") or "")[:19].replace("T", " "),
        ])

    data = "\ufeff" + buf.getvalue()
    filename = f"students_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        data.encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/admin/students")
def admin_create_student():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    payload = request.get_json(silent=True) or {}
    full_name = str(payload.get("fullName", "")).strip()
    class_name = str(payload.get("className", "")).strip()
    school = str(payload.get("school", "")).strip()

    if len(full_name) < 3:
        return jsonify({"error": "Ному насаб бояд камаш 3 ҳарф бошад."}), 400
    if not class_name:
        return jsonify({"error": "Синфро ворид кунед."}), 400
    if not school:
        return jsonify({"error": "Мактабро ворид кунед."}), 400

    code = generate_long_id()
    student = repo.create_student(code, full_name, class_name, school, admin["login"])
    return jsonify({"student": public_student(student)}), 201


@app.delete("/api/admin/students/<student_id>")
def admin_delete_student(student_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if not repo.delete_student(student_id):
        return jsonify({"error": "Хонанда ёфт нашуд."}), 404
    return jsonify({"ok": True})


@app.post("/api/student/login")
def student_login():
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("id", "")).strip()
    student = repo.find_student_by_code(student_id)
    if not student:
        return jsonify({"error": "ID нодуруст аст ё хонанда ёфт нашуд."}), 401
    return jsonify({"student": public_student(student)})


# ---------- Olympiads ----------

def normalize_time_field(value):
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text and len(text) == 16:
        text = text + ":00+05:00"
    dt = parse_dt(text)
    return dt.isoformat() if dt else text


@app.get("/api/admin/olympiads")
def admin_list_olympiads():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    items = repo.list_olympiads()
    return jsonify({"olympiads": [public_olympiad(o, include_answers=True) for o in items]})


@app.post("/api/admin/olympiads")
def admin_create_olympiad():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    otype = str(payload.get("type", "olympiad")).strip() or "olympiad"
    if otype not in ("olympiad", "quiz"):
        otype = "olympiad"
    try:
        pass_score = int(payload.get("passScore", 70))
    except (TypeError, ValueError):
        pass_score = 70
    pass_score = max(0, min(100, pass_score))

    start_time = normalize_time_field(payload.get("startTime"))
    end_time = normalize_time_field(payload.get("endTime"))
    if start_time and end_time:
        s, e = parse_dt(start_time), parse_dt(end_time)
        if s and e and e <= s:
            return jsonify({"error": "Вақти анҷом бояд баъд аз оғоз бошад."}), 400

    raw_questions = payload.get("questions") or []
    if not title:
        return jsonify({"error": "Унвонро ворид кунед."}), 400
    if not isinstance(raw_questions, list) or len(raw_questions) < 1:
        return jsonify({"error": "Камаш 1 савол лозим аст."}), 400

    questions = []
    for i, q in enumerate(raw_questions):
        text = str(q.get("text", "")).strip()
        options = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
        try:
            answer = int(q.get("answer", 0))
        except (TypeError, ValueError):
            answer = 0
        if not text or len(options) < 2:
            return jsonify({"error": f"Саволи {i + 1} нодуруст аст."}), 400
        if answer < 0 or answer >= len(options):
            return jsonify({"error": f"Ҷавоби дурусти саволи {i + 1} нодуруст аст."}), 400
        questions.append({"id": i + 1, "text": text, "options": options, "answer": answer})

    olympiad = repo.create_olympiad({
        "title": title,
        "type": otype,
        "passScore": pass_score,
        "isActive": bool(payload.get("isActive", False)),
        "startTime": start_time,
        "endTime": end_time,
        "questions": questions,
        "createdBy": admin["login"],
    })
    return jsonify({"olympiad": public_olympiad(olympiad, include_answers=True)}), 201


@app.patch("/api/admin/olympiads/<olympiad_id>")
def admin_update_olympiad(olympiad_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    payload = request.get_json(silent=True) or {}
    patch = {}
    if "isActive" in payload:
        patch["isActive"] = bool(payload["isActive"])
    if "passScore" in payload:
        try:
            patch["passScore"] = max(0, min(100, int(payload["passScore"])))
        except (TypeError, ValueError):
            pass
    if "title" in payload and str(payload["title"]).strip():
        patch["title"] = str(payload["title"]).strip()
    if "startTime" in payload:
        patch["startTime"] = normalize_time_field(payload.get("startTime"))
    if "endTime" in payload:
        patch["endTime"] = normalize_time_field(payload.get("endTime"))

    olympiad = repo.update_olympiad(olympiad_id, patch)
    if not olympiad:
        return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
    return jsonify({"olympiad": public_olympiad(olympiad, include_answers=True)})


@app.delete("/api/admin/olympiads/<olympiad_id>")
def admin_delete_olympiad(olympiad_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if not repo.delete_olympiad(olympiad_id):
        return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
    return jsonify({"ok": True})


@app.get("/api/olympiads/active")
def list_active_olympiads():
    items = repo.list_olympiads()
    active = [public_olympiad(o, include_answers=False) for o in items if is_olympiad_open(o)]
    return jsonify({"olympiads": active})


@app.post("/api/olympiads/<olympiad_id>/submit")
def submit_olympiad(olympiad_id: str):
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("studentId", "")).strip()
    answers = payload.get("answers") or []

    student = repo.find_student_by_code(student_id)
    if not student:
        return jsonify({"error": "Хонанда ёфт нашуд."}), 401

    olympiad = repo.find_olympiad(olympiad_id)
    if not olympiad:
        return jsonify({"error": "Олимпиада ёфт нашуд."}), 404

    window = olympiad_window_status(olympiad)
    if window == "inactive":
        return jsonify({"error": "Ин олимпиада ҳоло фаъол нест."}), 403
    if window == "not_started":
        return jsonify({"error": "Олимпиада ҳанӯз оғоз нашудааст."}), 403
    if window == "ended":
        return jsonify({"error": "Вақти олимпиада ба охир расид."}), 403

    questions = olympiad.get("questions") or []
    if not questions:
        return jsonify({"error": "Саволҳо нестанд."}), 400

    selected_map = {}
    if isinstance(answers, list):
        for i, a in enumerate(answers):
            if isinstance(a, dict):
                try:
                    qid = int(a.get("questionId", i + 1))
                    sel = int(a.get("selected"))
                except (TypeError, ValueError):
                    continue
                selected_map[qid] = sel
            else:
                try:
                    selected_map[i + 1] = int(a)
                except (TypeError, ValueError):
                    continue

    correct = 0
    detail = []
    for q in questions:
        qid = q["id"]
        right = int(q.get("answer", 0))
        sel = selected_map.get(qid)
        is_ok = sel is not None and sel == right
        if is_ok:
            correct += 1
        detail.append({"questionId": qid, "selected": sel, "correct": is_ok})

    total = len(questions)
    score = round((correct / total) * 100) if total else 0
    pass_score = int(olympiad.get("passScore", 70))
    status = "passed" if score >= pass_score else "failed"

    result = {
        "id": str(uuid.uuid4()),
        "studentId": student_id,
        "studentName": student.get("fullName"),
        "studentClass": student.get("className"),
        "studentSchool": student.get("school"),
        "olympiadId": olympiad_id,
        "olympiadTitle": olympiad.get("title"),
        "score": score,
        "correct": correct,
        "total": total,
        "passScore": pass_score,
        "status": status,
        "answers": detail,
        "finishedAt": utc_now(),
    }
    repo.save_result(result)

    return jsonify({
        "result": {
            "score": score,
            "correct": correct,
            "total": total,
            "passScore": pass_score,
            "status": status,
            "finishedAt": result["finishedAt"],
        }
    })


@app.get("/api/admin/olympiads/<olympiad_id>/results")
def admin_olympiad_results(olympiad_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    filtered = repo.list_results(olympiad_id)
    filtered.sort(key=lambda r: r.get("finishedAt") or "", reverse=True)
    return jsonify({"results": filtered})


@app.get("/api/admin/monitor")
def admin_monitor():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    students = repo.list_students()
    olympiads = repo.list_olympiads()
    results = repo.list_results()

    return jsonify({
        "backend": repo.backend_name(),
        "stats": {
            "students": len(students),
            "olympiads": len(olympiads),
            "activeOlympiads": sum(1 for o in olympiads if is_olympiad_open(o)),
            "results": len(results),
            "passed": sum(1 for r in results if r.get("status") == "passed"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
        },
        "recentResults": sorted(
            results, key=lambda r: r.get("finishedAt") or "", reverse=True
        )[:30],
    })


@app.route("/<path:path>")
def static_proxy(path):
    normalized_path = path.replace("\\", "/")
    if normalized_path not in PUBLIC_PATHS:
        return abort(404)

    file_path = (BASE_DIR / path).resolve()
    if BASE_DIR not in file_path.parents and file_path != BASE_DIR:
        return abort(404)
    if file_path.is_file():
        return send_from_directory(BASE_DIR, path)
    return abort(404)


ensure_json_file(USERS_FILE)
ensure_json_file(ADMINS_FILE, default="[]")
ensure_json_file(STUDENTS_FILE)
ensure_json_file(OLYMPIADS_FILE)
ensure_json_file(RESULTS_FILE)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
