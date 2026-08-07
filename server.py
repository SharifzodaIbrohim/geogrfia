from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

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
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Token, X-Student-Id"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    if request.method == "OPTIONS":
        response.status_code = 204
    return response


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_json_file(path: Path, default="[]") -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not path.exists():
        path.write_text(default, encoding="utf-8")


def load_json(path: Path) -> list | dict:
    ensure_json_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return [] if path != ADMINS_FILE else []
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
    """19-digit unique student ID."""
    students = load_json(STUDENTS_FILE)
    existing = {s.get("id") for s in students if isinstance(s, dict)}
    for _ in range(50):
        # 19 digits, does not start with 0
        num = secrets.randbelow(9 * 10**18) + 10**18
        sid = str(num)
        if sid not in existing:
            return sid
    return str(uuid.uuid4().int)[:19]


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "createdAt": user["createdAt"],
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
    return {
        "id": o["id"],
        "title": o["title"],
        "type": o.get("type", "olympiad"),
        "passScore": o.get("passScore", 70),
        "isActive": bool(o.get("isActive")),
        "startTime": o.get("startTime"),
        "endTime": o.get("endTime"),
        "questions": questions,
        "questionCount": len(questions),
        "createdAt": o.get("createdAt"),
        "createdBy": o.get("createdBy"),
    }


# Simple in-memory admin tokens (enough for phase 1)
ADMIN_TOKENS: dict[str, dict] = {}


def create_admin_token(admin: dict) -> str:
    token = secrets.token_hex(24)
    ADMIN_TOKENS[token] = {
        "id": admin["id"],
        "login": admin["login"],
        "name": admin.get("name", admin["login"]),
    }
    return token


def require_admin():
    token = request.headers.get("X-Admin-Token", "")
    admin = ADMIN_TOKENS.get(token)
    if not admin:
        return None
    return admin


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


# ---------- Existing public auth (legacy) ----------

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

    with LOCK:
        users = load_json(USERS_FILE)
        if not isinstance(users, list):
            users = []
        if any(user.get("email") == email for user in users):
            return jsonify({"error": "Ин email аллакай сабт шудааст."}), 409

        salt, password_hash = hash_password(password)
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

    users = load_json(USERS_FILE)
    if not isinstance(users, list):
        users = []
    user = next((item for item in users if item.get("email") == email), None)
    if not user or not verify_password(password, user.get("salt", ""), user.get("passwordHash", "")):
        return jsonify({"error": "Email ё парол нодуруст аст."}), 401

    return jsonify({"user": public_user(user)})


# ---------- Admin auth ----------

@app.post("/api/admin/login")
def admin_login():
    payload = request.get_json(silent=True) or {}
    login_name = str(payload.get("login", "")).strip()
    password = str(payload.get("password", ""))

    admins = load_json(ADMINS_FILE)
    if not isinstance(admins, list):
        admins = []
    admin = next((a for a in admins if a.get("login") == login_name), None)
    if not admin or not verify_password(password, admin.get("salt", ""), admin.get("passwordHash", "")):
        return jsonify({"error": "Логин ё парол нодуруст аст."}), 401

    token = create_admin_token(admin)
    return jsonify({
        "token": token,
        "admin": {"id": admin["id"], "login": admin["login"], "name": admin.get("name", admin["login"])},
    })


@app.get("/api/admin/me")
def admin_me():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    return jsonify({"admin": admin})


# ---------- Students (admin only create) ----------

@app.get("/api/admin/students")
def admin_list_students():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    students = load_json(STUDENTS_FILE)
    if not isinstance(students, list):
        students = []
    return jsonify({"students": [public_student(s) for s in students]})


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

    with LOCK:
        students = load_json(STUDENTS_FILE)
        if not isinstance(students, list):
            students = []
        student = {
            "id": generate_long_id(),
            "fullName": full_name,
            "className": class_name,
            "school": school,
            "createdBy": admin["login"],
            "createdAt": utc_now(),
        }
        students.append(student)
        save_json(STUDENTS_FILE, students)

    return jsonify({"student": public_student(student)}), 201


@app.delete("/api/admin/students/<student_id>")
def admin_delete_student(student_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    with LOCK:
        students = load_json(STUDENTS_FILE)
        if not isinstance(students, list):
            students = []
        new_list = [s for s in students if s.get("id") != student_id]
        if len(new_list) == len(students):
            return jsonify({"error": "Хонанда ёфт нашуд."}), 404
        save_json(STUDENTS_FILE, new_list)
    return jsonify({"ok": True})


# ---------- Student login by long ID ----------

@app.post("/api/student/login")
def student_login():
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("id", "")).strip()

    students = load_json(STUDENTS_FILE)
    if not isinstance(students, list):
        students = []
    student = next((s for s in students if s.get("id") == student_id), None)
    if not student:
        return jsonify({"error": "ID нодуруст аст ё хонанда ёфт нашуд."}), 401

    return jsonify({"student": public_student(student)})


# ---------- Olympiads ----------

@app.get("/api/admin/olympiads")
def admin_list_olympiads():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401
    items = load_json(OLYMPIADS_FILE)
    if not isinstance(items, list):
        items = []
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
        questions.append({
            "id": i + 1,
            "text": text,
            "options": options,
            "answer": answer,
        })

    olympiad = {
        "id": str(uuid.uuid4()),
        "title": title,
        "type": otype,
        "passScore": pass_score,
        "isActive": bool(payload.get("isActive", False)),
        "startTime": payload.get("startTime"),
        "endTime": payload.get("endTime"),
        "questions": questions,
        "createdBy": admin["login"],
        "createdAt": utc_now(),
    }

    with LOCK:
        items = load_json(OLYMPIADS_FILE)
        if not isinstance(items, list):
            items = []
        items.append(olympiad)
        save_json(OLYMPIADS_FILE, items)

    return jsonify({"olympiad": public_olympiad(olympiad, include_answers=True)}), 201


@app.patch("/api/admin/olympiads/<olympiad_id>")
def admin_update_olympiad(olympiad_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    payload = request.get_json(silent=True) or {}

    with LOCK:
        items = load_json(OLYMPIADS_FILE)
        if not isinstance(items, list):
            items = []
        olympiad = next((o for o in items if o.get("id") == olympiad_id), None)
        if not olympiad:
            return jsonify({"error": "Олимпиада ёфт нашуд."}), 404

        if "isActive" in payload:
            olympiad["isActive"] = bool(payload["isActive"])
        if "passScore" in payload:
            try:
                olympiad["passScore"] = max(0, min(100, int(payload["passScore"])))
            except (TypeError, ValueError):
                pass
        if "title" in payload and str(payload["title"]).strip():
            olympiad["title"] = str(payload["title"]).strip()

        save_json(OLYMPIADS_FILE, items)

    return jsonify({"olympiad": public_olympiad(olympiad, include_answers=True)})


@app.delete("/api/admin/olympiads/<olympiad_id>")
def admin_delete_olympiad(olympiad_id: str):
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    with LOCK:
        items = load_json(OLYMPIADS_FILE)
        if not isinstance(items, list):
            items = []
        new_list = [o for o in items if o.get("id") != olympiad_id]
        if len(new_list) == len(items):
            return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
        save_json(OLYMPIADS_FILE, new_list)
    return jsonify({"ok": True})


@app.get("/api/olympiads/active")
def list_active_olympiads():
    """For students — only active olympiads, without correct answers."""
    items = load_json(OLYMPIADS_FILE)
    if not isinstance(items, list):
        items = []
    active = [public_olympiad(o, include_answers=False) for o in items if o.get("isActive")]
    return jsonify({"olympiads": active})


@app.post("/api/olympiads/<olympiad_id>/submit")
def submit_olympiad(olympiad_id: str):
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("studentId", "")).strip()
    answers = payload.get("answers") or []

    students = load_json(STUDENTS_FILE)
    if not isinstance(students, list):
        students = []
    student = next((s for s in students if s.get("id") == student_id), None)
    if not student:
        return jsonify({"error": "Хонанда ёфт нашуд."}), 401

    items = load_json(OLYMPIADS_FILE)
    if not isinstance(items, list):
        items = []
    olympiad = next((o for o in items if o.get("id") == olympiad_id), None)
    if not olympiad:
        return jsonify({"error": "Олимпиада ёфт нашуд."}), 404
    if not olympiad.get("isActive"):
        return jsonify({"error": "Ин олимпиада ҳоло фаъол нест."}), 403

    questions = olympiad.get("questions") or []
    if not questions:
        return jsonify({"error": "Саволҳо нестанд."}), 400

    # answers: list of {questionId, selected} or list of ints in order
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

    with LOCK:
        results = load_json(RESULTS_FILE)
        if not isinstance(results, list):
            results = []
        # replace previous attempt for same student+olympiad
        results = [
            r for r in results
            if not (r.get("studentId") == student_id and r.get("olympiadId") == olympiad_id)
        ]
        results.append(result)
        save_json(RESULTS_FILE, results)

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

    results = load_json(RESULTS_FILE)
    if not isinstance(results, list):
        results = []
    filtered = [r for r in results if r.get("olympiadId") == olympiad_id]
    filtered.sort(key=lambda r: r.get("finishedAt") or "", reverse=True)
    return jsonify({"results": filtered})


@app.get("/api/admin/monitor")
def admin_monitor():
    admin = require_admin()
    if not admin:
        return jsonify({"error": "Дастрасӣ рад шуд."}), 401

    students = load_json(STUDENTS_FILE)
    olympiads = load_json(OLYMPIADS_FILE)
    results = load_json(RESULTS_FILE)
    if not isinstance(students, list):
        students = []
    if not isinstance(olympiads, list):
        olympiads = []
    if not isinstance(results, list):
        results = []

    return jsonify({
        "stats": {
            "students": len(students),
            "olympiads": len(olympiads),
            "activeOlympiads": sum(1 for o in olympiads if o.get("isActive")),
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
