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
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERS_LOCK = threading.Lock()
PUBLIC_PATHS = {
    "index.html",
    "css/style.css",
    "js/app.js",
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
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def ensure_users_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def load_users() -> list[dict]:
    ensure_users_file()
    try:
        users = json.loads(USERS_FILE.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    if not isinstance(users, list):
        return []
    return [user for user in users if isinstance(user, dict)]


def save_users(users: list[dict]) -> None:
    ensure_users_file()
    payload = json.dumps(users, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=DATA_DIR,
        delete=False,
        prefix="users-",
        suffix=".tmp",
    ) as temp_file:
        temp_file.write(payload)
        temp_name = temp_file.name
    Path(temp_name).replace(USERS_FILE)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        120_000,
    ).hex()
    return salt, password_hash


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "createdAt": user["createdAt"],
    }


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


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

    with USERS_LOCK:
        users = load_users()
        if any(user.get("email") == email for user in users):
            return jsonify({"error": "Ин email аллакай сабт шудааст."}), 409

        salt, password_hash = hash_password(password)
        user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "salt": salt,
            "passwordHash": password_hash,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        users.append(user)
        save_users(users)
    return jsonify({"user": public_user(user)}), 201


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    users = load_users()
    user = next((item for item in users if item.get("email") == email), None)
    if not user:
        return jsonify({"error": "Email ё парол нодуруст аст."}), 401

    salt = user.get("salt")
    stored_hash = user.get("passwordHash")
    if not salt or not stored_hash:
        return jsonify({"error": "Email ё парол нодуруст аст."}), 401

    _, password_hash = hash_password(password, salt)
    if not secrets.compare_digest(password_hash, stored_hash):
        return jsonify({"error": "Email ё парол нодуруст аст."}), 401

    return jsonify({"user": public_user(user)})


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


# Ensure users file exists when the app starts (for gunicorn too)
ensure_users_file()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
