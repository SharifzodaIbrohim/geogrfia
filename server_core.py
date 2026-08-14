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


# === Phase mid-layer (was remote 12d7430) ===

from db.phase23_hooks import (  # noqa: E402
    create_user_token as _jwt_user_token,
    require_admin as _jwt_require_admin,
    require_user as _jwt_require_user,
    register_routes,
)
from db import student_access  # noqa: E402
from db.admin_role import enrich_admin, create_admin_with_role, update_admin_role  # noqa: E402
from db.rbac import admin_can, deny_message, role_permissions, normalize_role, VALID_ROLES  # noqa: E402
from db.auth_tokens import issue_admin_token  # noqa: E402
from db import schools_api  # noqa: E402
from db.quiz_routes import register_quiz_routes  # noqa: E402
from db.olympiad_routes import register_olympiad_engine_routes  # noqa: E402
from db.reports_routes import register_reports_routes  # noqa: E402
from db.audit_routes import register_audit_routes  # noqa: E402
from db import audit  # noqa: E402
from db import notifications  # noqa: E402
import hashlib  # noqa: E402
import secrets  # noqa: E402

try:
    PUBLIC_PATHS.update({
        "quiz.html",
        "countries.html",
        "css/quiz.css",
        "css/platform.css",
        "js/quiz-platform.js",
        "js/platform.js",
        "js/platform-home.js",
        "js/admin-audit.js",
    })
except Exception:
    pass


def _hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()
    return salt, password_hash


def create_admin_token(admin: dict) -> str:
    admin = enrich_admin(dict(admin)) or admin
    return issue_admin_token(admin)


def require_admin():
    admin = _jwt_require_admin()
    return enrich_admin(admin) if admin else None


def require_perm(*perms: str):
    admin = require_admin()
    if not admin:
        return None
    if any(admin_can(admin, p) for p in perms):
        return admin
    return False


globals()["create_admin_token"] = create_admin_token
globals()["create_user_token"] = _jwt_user_token
globals()["require_admin"] = require_admin
globals()["require_user"] = _jwt_require_user

_orig_submit = globals().get("submit_olympiad")


def submit_olympiad(olympiad_id: str):
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("studentId", "")).strip()
    if student_id and olympiad_id:
        access = student_access.student_has_olympiad_access(olympiad_id, student_id)
        if not access.get("allowed"):
            reason = access.get("reason")
            msg = (
                "Шумо ба ин олимпиада таъин нашудаед."
                if reason == "not_assigned"
                else "Дастрасӣ рад шуд."
            )
            return jsonify({"error": msg, "reason": reason}), 403
    resp = _orig_submit(olympiad_id)
    try:
        if getattr(resp, "status_code", 500) < 400:
            data = resp.get_json() or {}
            result = data.get("result") or data
            if result.get("score") is not None:
                notifications.notify_result(result)
    except Exception:
        pass
    return resp


globals()["submit_olympiad"] = submit_olympiad
app.view_functions["submit_olympiad"] = submit_olympiad

register_routes(app, public_student, public_user, olympiad_window_status)
register_quiz_routes(app, _jwt_require_user, require_perm)
register_olympiad_engine_routes(app, _jwt_require_user, olympiad_window_status)
register_reports_routes(app, require_perm, require_admin)
register_audit_routes(app, require_perm, require_admin)


@app.after_request
def _audit_admin_mutations(response):
    try:
        if not request.path.startswith("/api/admin/"):
            return response
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response
        if response.status_code >= 400:
            return response
        if request.path.endswith("/notifications/test"):
            return response
        admin = require_admin()
        if not admin:
            return response
        action = f"{request.method} {request.path}"
        audit.log_action(
            action=action,
            admin=admin,
            target_type="api",
            target_id=request.path,
            meta={"status": response.status_code},
            ip=request.headers.get("X-Forwarded-For", request.remote_addr),
        )
        if request.method == "POST" and "/olympiads" in request.path and "leaderboard" not in request.path:
            try:
                data = response.get_json(silent=True) or {}
                oly = data.get("olympiad") or data
                if oly.get("title") or oly.get("id"):
                    notifications.notify_olympiad_event("created", oly)
            except Exception:
                pass
        if request.method == "POST" and "/quizzes" in request.path:
            try:
                data = response.get_json(silent=True) or {}
                q = data.get("quiz") or {}
                if q.get("title"):
                    notifications.create_notification(
                        title="Викторинаи нав",
                        body=q.get("title"),
                        link="/quiz",
                        audience="admin",
                    )
            except Exception:
                pass
    except Exception:
        pass
    return response


@app.route("/quiz")
@app.route("/quiz.html")
def quiz_page():
    return send_from_directory(BASE_DIR, "quiz.html")


@app.route("/countries")
@app.route("/countries.html")
def countries_page():
    return send_from_directory(BASE_DIR, "countries.html")


def admin_me():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    role = normalize_role(admin.get("role"))
    return jsonify({
        "admin": {
            "id": admin.get("id"),
            "login": admin.get("login"),
            "name": admin.get("name"),
            "role": role,
        },
        "permissions": sorted(role_permissions(role)),
        "backend": repo.backend_name(),
    })


app.view_functions["admin_me"] = admin_me

_orig_admin_login = app.view_functions.get("admin_login")


def admin_login():
    resp = _orig_admin_login()
    if getattr(resp, "status_code", 200) != 200:
        return resp
    try:
        data = resp.get_json()
        login_name = (data.get("admin") or {}).get("login")
        if login_name:
            from db.repo import find_admin_by_login

            full = enrich_admin(find_admin_by_login(login_name))
            if full:
                token = create_admin_token(full)
                data["token"] = token
                data["admin"] = {
                    "id": full.get("id"),
                    "login": full.get("login"),
                    "name": full.get("name"),
                    "role": normalize_role(full.get("role")),
                    "createdAt": full.get("createdAt"),
                    "createdBy": full.get("createdBy"),
                }
                data["permissions"] = sorted(role_permissions(full.get("role")))
                try:
                    audit.log_action(
                        action="admin.login",
                        admin=full,
                        target_type="admin",
                        target_id=full.get("id"),
                        ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                    )
                except Exception:
                    pass
                return jsonify(data)
    except Exception:
        pass
    return resp


app.view_functions["admin_login"] = admin_login


def _gate(view_name: str, *perms: str):
    orig = app.view_functions.get(view_name)
    if not orig:
        return

    def wrapper(*args, **kwargs):
        admin = require_perm(*perms)
        if admin is None:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401
        if admin is False:
            return jsonify({"error": deny_message(perms[0])}), 403
        return orig(*args, **kwargs)

    wrapper.__name__ = view_name
    app.view_functions[view_name] = wrapper


_gate("admin_list_students", "students.read")
_gate("admin_create_student", "students.write")
_gate("admin_delete_student", "students.write")
_gate("admin_export_students", "students.read")
_gate("admin_list_olympiads", "olympiads.read")
_gate("admin_create_olympiad", "olympiads.write")
_gate("admin_update_olympiad", "olympiads.write")
_gate("admin_delete_olympiad", "olympiads.write")
_gate("admin_olympiad_results", "results.read")
_gate("admin_monitor", "monitor.read")
_gate("admin_list_admins", "admins.read")
_gate("admin_delete_admin", "admins.write")
_gate("admin_list_participants", "olympiads.read", "participants.write")
_gate("admin_set_participants", "participants.write")


def admin_create_admin():
    admin = require_perm("admins.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False or normalize_role(admin.get("role")) != "super_admin":
        return jsonify({"error": "Танҳо Super Admin метавонад админ созад."}), 403

    payload = request.get_json(silent=True) or {}
    login_name = str(payload.get("login", "")).strip()
    name = str(payload.get("name", "")).strip() or login_name
    password = str(payload.get("password", ""))
    role = normalize_role(payload.get("role") or "olympiad_admin")

    if len(login_name) < 3:
        return jsonify({"error": "Логин бояд камаш 3 рамз бошад."}), 400
    if len(password) < 6:
        return jsonify({"error": "Парол бояд камаш 6 рамз бошад."}), 400
    from db.repo import find_admin_by_login

    if find_admin_by_login(login_name):
        return jsonify({"error": "Ин логин аллакай вуҷуд дорад."}), 409

    salt, password_hash = _hash_password(password)
    new_admin = create_admin_with_role(
        login_name, name, salt, password_hash, admin["login"], role=role
    )
    return jsonify({"admin": new_admin}), 201


app.view_functions["admin_create_admin"] = admin_create_admin


@app.patch("/api/admin/admins/<admin_id>/role")
def admin_patch_role(admin_id: str):
    admin = require_perm("admins.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False or normalize_role(admin.get("role")) != "super_admin":
        return jsonify({"error": "Танҳо Super Admin."}), 403
    payload = request.get_json(silent=True) or {}
    role = normalize_role(payload.get("role"))
    if role not in VALID_ROLES:
        return jsonify({"error": "Нақши нодуруст.", "valid": list(VALID_ROLES)}), 400
    if not update_admin_role(admin_id, role):
        return jsonify({"error": "Админ ёфт нашуд."}), 404
    return jsonify({"ok": True, "id": admin_id, "role": role})


@app.get("/api/admin/roles")
def admin_list_roles():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({
        "roles": [
            {"id": r, "permissions": sorted(role_permissions(r))}
            for r in VALID_ROLES
        ]
    })


@app.get("/api/admin/dashboard")
def admin_dashboard():
    admin = require_perm("monitor.read", "students.read")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("monitor.read")}), 403
    return jsonify(schools_api.dashboard_stats())


@app.get("/api/admin/schools")
def admin_list_schools():
    admin = require_perm("schools.read", "students.read")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("schools.read")}), 403
    return jsonify({"schools": schools_api.list_schools()})


@app.post("/api/admin/schools")
def admin_create_school():
    admin = require_perm("schools.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("schools.write")}), 403
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    location = str(payload.get("location", "") or "").strip() or None
    if len(name) < 2:
        return jsonify({"error": "Номи мактаб лозим аст."}), 400
    try:
        school = schools_api.create_school(name, location)
    except ValueError:
        return jsonify({"error": "Ин мактаб аллакай вуҷуд дорад."}), 409
    return jsonify({"school": school}), 201


@app.delete("/api/admin/schools/<school_id>")
def admin_delete_school(school_id: str):
    admin = require_perm("schools.write")
    if admin is None:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    if admin is False:
        return jsonify({"error": deny_message("schools.write")}), 403
    if not schools_api.delete_school(school_id):
        return jsonify({"error": "Мактаб ёфт нашуд."}), 404
    return jsonify({"ok": True})


# === Phase top patches (was remote loader + local) ===

try:
    PUBLIC_PATHS.update({
        "profile.html", "courses.html", "leaderboard.html",
        "css/profile.css", "js/profile.js", "js/admin-gmail.js",
        "js/i18n.js", "js/admin-content.js", "js/platform-home.js",
        "js/admin-leaderboard.js", "js/admin-fixes.js",
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

# Gmail open access + real name
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

# Content API hard fallback
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
        data_dir = None
        for cand in [BASE_DIR / "data", _P.cwd() / "data"]:
            try:
                cand.mkdir(parents=True, exist_ok=True)
                data_dir = cand
                break
            except Exception:
                continue
        path = (data_dir or _P.cwd()) / "content_items.json"
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
            items = [{
                "id": str(_uuid.uuid4()), "type": b["type"], "title": b["title"],
                "description": "", "url": b["url"], "lang": b["lang"], "createdAt": now,
            } for b in _DEFAULT_BOOKS]
            try:
                import json as _json
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

# Global leaderboard API
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
        settings = _ld("leaderboard_settings.json") or {"public": True, "title": "Leaderboard \u00b7 Top Rated", "useDemo": True}
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
            by[uid] = {
                "id": uid, "name": name or "Иштирокчӣ",
                "school": u.get("school") or "", "className": u.get("className") or "",
                "rating": int(u.get("rating") or 1200), "solved": 0, "contests": 0,
            }
        students = _ld("students.json") or []
        if isinstance(students, list):
            for st in students:
                sid = str(st.get("id") or "")
                if not sid:
                    continue
                by[sid] = {
                    "id": sid,
                    "name": (st.get("fullName") or st.get("name") or "Хонанда"),
                    "school": st.get("school") or "", "className": st.get("className") or "",
                    "rating": int(st.get("rating") or 1200), "solved": 0, "contests": 0,
                }
        rows = sorted(by.values(), key=lambda x: -int(x.get("rating") or 0))
        demo = False
        if not rows and settings.get("useDemo", True):
            demo = True
            rows = [
                {"id": "demo-1", "name": "Ализода Фарход", "school": "Литсей №1", "className": "11А", "rating": 1480, "solved": 12, "contests": 5},
                {"id": "demo-2", "name": "Каримова Дилбар", "school": "МТМУ №15", "className": "10Б", "rating": 1410, "solved": 9, "contests": 4},
                {"id": "demo-3", "name": "Раҳимов Ҷамолиддин", "school": "Литсей №2", "className": "11Б", "rating": 1365, "solved": 8, "contests": 3},
            ]
        entries = []
        for i, r in enumerate(rows[:limit], 1):
            e = dict(r)
            e["rank"] = i
            entries.append(e)
        return {"public": True, "title": settings.get("title") or "Leaderboard \u00b7 Top Rated", "entries": entries, "total": len(rows), "demo": demo, "settings": settings}

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
        try:
            limit = min(500, max(1, int(_rl.args.get("limit") or 200)))
        except Exception:
            limit = 200
        return _jl(_lb_build(limit=limit, public_only=False))

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
            return _jl({"public": True, "title": "Leaderboard \u00b7 Top Rated", "pinned": []})

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
            cur = {"public": True, "title": "Leaderboard \u00b7 Top Rated", "pinned": []}
            if path.exists():
                try:
                    cur = _json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            cur.update({k: payload[k] for k in ("public", "title", "showSchool", "showClass", "pinned", "useDemo") if k in payload})
            path.write_text(_json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
            return _jl(cur)
except Exception:
    pass

# Force Gmail-capable quiz_start
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
        payload = _req.get_json(silent=True) or {}
        student_code = str(
            payload.get("studentId") or _req.headers.get("X-Student-Id") or ""
        ).strip() or None
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
                if user and user.get("id"):
                    student_code = "g:" + str(user["id"])[:40]
                else:
                    return jsonify({
                        "error": "Аввал бо Google ворид шавед ё Student ID ворид кунед.",
                        "reason": "google_or_student_required",
                    }), 403
            try:
                session = _oe.start_exam(
                    quiz_id,
                    student_code,
                    user_id=user["id"] if user else None,
                    client_fingerprint=fp or None,
                )
            except ValueError as e:
                code = str(e)
                msgs = {
                    "rate_limited": "Зиёд дархост.",
                    "already_submitted": "Аллакай супоридаед. Танҳо 1 бор ичоза аст.",
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
            attempt = _qa.start_attempt(
                quiz_id,
                user_id=user["id"] if user else None,
                student_id=student_code,
            )
        except ValueError as e:
            code = str(e)
            if code == "already_submitted":
                return jsonify({"error": "Аллакай супоридаед. Танҳо 1 бор ичоза аст.", "reason": code}), 403
            return jsonify({"error": str(e)}), 400
        attempt["source"] = "quiz"
        return jsonify(attempt)

    app.view_functions["quiz_start"] = _patched_quiz_start
except Exception:
    pass

# Clear results + olympiad LB public
try:
    from flask import jsonify as _jc, request as _rc
    import json as _json_cr

    @app.post("/api/admin/results/clear-recent")
    def _clear_recent_results():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jc({"error": "Дастрасӣ рад шуд."}), 401
        return _jc({"ok": True, "message": "UI пок шуд"})

    @app.post("/api/admin/results/clear-all")
    def _clear_all_results():
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jc({"error": "Дастрасӣ рад шуд."}), 401
        cleared = 0
        for name in ("results.json",):
            path = BASE_DIR / "data" / name
            if path.exists():
                try:
                    data = _json_cr.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        cleared = len(data)
                    path.write_text("[]", encoding="utf-8")
                except Exception as e:
                    return _jc({"error": str(e)}), 500
        try:
            from db.connection import get_session
            from sqlalchemy import text
            with get_session() as s:
                s.execute(text("DELETE FROM results"))
        except Exception:
            pass
        return _jc({"ok": True, "cleared": cleared})

    @app.route("/api/admin/olympiads/<oid>/leaderboard", methods=["GET", "PATCH"])
    def _oly_leaderboard_public(oid):
        try:
            admin = require_admin()
        except Exception:
            admin = None
        if not admin:
            return _jc({"error": "Дастрасӣ рад шуд."}), 401
        settings_path = BASE_DIR / "data" / "olympiad_lb_settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        all_s = {}
        if settings_path.exists():
            try:
                all_s = _json_cr.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                all_s = {}
        if not isinstance(all_s, dict):
            all_s = {}
        cur = all_s.get(str(oid)) or {"public": True}
        if _rc.method == "PATCH":
            payload = _rc.get_json(silent=True) or {}
            if "public" in payload:
                cur["public"] = bool(payload["public"])
            all_s[str(oid)] = cur
            settings_path.write_text(_json_cr.dumps(all_s, ensure_ascii=False, indent=2), encoding="utf-8")
            return _jc({"ok": True, "leaderboardPublic": cur.get("public", True), "olympiadId": oid})
        return _jc({"entries": [], "leaderboard": [], "leaderboardPublic": cur.get("public", True), "olympiadId": oid})
except Exception:
    pass

# Fix bridged quiz list accessMode
try:
    from flask import jsonify as _jq
    from db import quiz_api as _qapi
    from db import quiz_bridge as _qbr

    def _public_list_quizzes_fixed():
        items = _qapi.list_quizzes(include_draft=False)
        safe = []
        seen = set()
        for q in items:
            seen.add(q["id"])
            safe.append({
                "id": q["id"],
                "title": q.get("title"),
                "description": q.get("description"),
                "passScore": q.get("passScore"),
                "timeLimitSec": q.get("timeLimitSec"),
                "accessMode": q.get("accessMode") or "public",
                "schoolName": q.get("schoolName"),
                "questionCount": q.get("questionCount") or 0,
                "source": "quiz",
            })
        # Olympiads never on public /quiz
        return _jq({"quizzes": safe})

    app.view_functions["public_list_quizzes"] = _public_list_quizzes_fixed
except Exception:
    pass

# One attempt only (no retake after submit)
try:
    from db.one_attempt import install as _install_one_attempt
    _install_one_attempt()
except Exception:
    pass

# FINAL: force public quiz list = standalone only
try:
    from db.force_public_quiz_list import install as _install_strict_quiz_list
    _install_strict_quiz_list(app)
except Exception as _e:
    print("[boot] force_public_quiz_list:", _e)
