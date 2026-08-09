"""
Ensure admin dicts include role from PostgreSQL (or JSON default).
Patches repo.find_admin_by_login / list_admins / create_admin when possible.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.rbac import VALID_ROLES, normalize_role
from db.repo import use_pg, _load_json, _save_json, ADMINS_FILE, _utc_now


def fetch_role_by_login(login: str) -> str | None:
    if not use_pg():
        return None
    with get_session() as s:
        r = s.execute(
            text("SELECT role::text FROM admins WHERE login = :l"),
            {"l": login},
        ).scalar()
        return str(r) if r else None


def fetch_role_by_id(admin_id: str) -> str | None:
    if not use_pg():
        return None
    with get_session() as s:
        r = s.execute(
            text("SELECT role::text FROM admins WHERE id::text = :id"),
            {"id": admin_id},
        ).scalar()
        return str(r) if r else None


def enrich_admin(admin: dict | None) -> dict | None:
    if not admin:
        return None
    if admin.get("role"):
        admin["role"] = normalize_role(admin["role"])
        return admin
    role = None
    if admin.get("login"):
        role = fetch_role_by_login(admin["login"])
    if not role and admin.get("id"):
        role = fetch_role_by_id(str(admin["id"]))
    admin["role"] = normalize_role(role)
    return admin


def create_admin_with_role(
    login: str,
    name: str,
    salt: str,
    password_hash: str,
    created_by: str,
    role: str = "olympiad_admin",
) -> dict:
    role = normalize_role(role)
    if role not in VALID_ROLES:
        role = "olympiad_admin"
    # only allow non-super by default for new admins unless creator is super
    aid = str(uuid.uuid4())
    created = _utc_now()
    if use_pg():
        with get_session() as s:
            s.execute(
                text(
                    "INSERT INTO admins (id, login, name, salt, password_hash, role, created_by) "
                    "VALUES (:id, :login, :name, :salt, :ph, CAST(:role AS admin_role), :cb)"
                ),
                {
                    "id": aid,
                    "login": login,
                    "name": name,
                    "salt": salt,
                    "ph": password_hash,
                    "role": role,
                    "cb": created_by,
                },
            )
        return {
            "id": aid,
            "login": login,
            "name": name,
            "role": role,
            "createdBy": created_by,
            "createdAt": created,
        }
    admins = _load_json(ADMINS_FILE)
    row = {
        "id": aid,
        "login": login,
        "name": name,
        "salt": salt,
        "passwordHash": password_hash,
        "role": role,
        "createdBy": created_by,
        "createdAt": created,
    }
    admins.append(row)
    _save_json(ADMINS_FILE, admins)
    return {k: row[k] for k in ("id", "login", "name", "role", "createdBy", "createdAt")}


def update_admin_role(admin_id: str, role: str) -> bool:
    role = normalize_role(role)
    if use_pg():
        with get_session() as s:
            res = s.execute(
                text(
                    "UPDATE admins SET role = CAST(:role AS admin_role) WHERE id::text = :id"
                ),
                {"role": role, "id": admin_id},
            )
            return res.rowcount > 0
    admins = _load_json(ADMINS_FILE)
    for a in admins:
        if a.get("id") == admin_id:
            a["role"] = role
            _save_json(ADMINS_FILE, admins)
            return True
    return False


def list_admins_with_roles() -> list[dict]:
    from db import repo

    items = repo.list_admins()
    out = []
    for a in items:
        out.append(enrich_admin(dict(a)))
    return out
