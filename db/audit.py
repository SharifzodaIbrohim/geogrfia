"""Phase 17 — Audit log for important admin actions."""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.repo import use_pg, DATA_DIR, _load_json, _save_json, _utc_now

AUDIT_FILE = DATA_DIR / "audit_logs.json"


def log_action(
    *,
    action: str,
    admin: dict | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    meta: dict | None = None,
    ip: str | None = None,
) -> None:
    if not action:
        return
    entry = {
        "id": str(uuid.uuid4()),
        "adminId": (admin or {}).get("id"),
        "adminLogin": (admin or {}).get("login"),
        "action": action,
        "targetType": target_type,
        "targetId": str(target_id) if target_id is not None else None,
        "meta": meta or {},
        "ip": ip,
        "createdAt": _utc_now(),
    }
    try:
        if use_pg():
            with get_session() as s:
                s.execute(
                    text(
                        "INSERT INTO audit_logs "
                        "(admin_id, admin_login, action, target_type, target_id, meta, ip) "
                        "VALUES (:aid, :login, :action, :tt, :tid, CAST(:meta AS jsonb), :ip)"
                    ),
                    {
                        "aid": entry["adminId"] if entry["adminId"] else None,
                        "login": entry["adminLogin"],
                        "action": action,
                        "tt": target_type,
                        "tid": entry["targetId"],
                        "meta": json.dumps(meta or {}),
                        "ip": ip,
                    },
                )
        else:
            items = _load_json(AUDIT_FILE)
            items.append(entry)
            # keep last 2000
            if len(items) > 2000:
                items = items[-2000:]
            _save_json(AUDIT_FILE, items)
    except Exception:
        # never break main request because of audit failure
        try:
            items = _load_json(AUDIT_FILE)
            items.append(entry)
            _save_json(AUDIT_FILE, items[-2000:])
        except Exception:
            pass


def list_audit(
    *,
    limit: int = 100,
    action: str | None = None,
    admin_login: str | None = None,
) -> list[dict]:
    limit = max(1, min(int(limit or 100), 500))
    if use_pg():
        try:
            q = (
                "SELECT id, admin_login, action, target_type, target_id, meta, ip, created_at "
                "FROM audit_logs WHERE 1=1 "
            )
            params: dict[str, Any] = {"lim": limit}
            if action:
                q += "AND action = :action "
                params["action"] = action
            if admin_login:
                q += "AND admin_login = :login "
                params["login"] = admin_login
            q += "ORDER BY created_at DESC LIMIT :lim"
            with get_session() as s:
                rows = s.execute(text(q), params).mappings().all()
            return [
                {
                    "id": str(r["id"]),
                    "adminLogin": r["admin_login"],
                    "action": r["action"],
                    "targetType": r["target_type"],
                    "targetId": r["target_id"],
                    "meta": r["meta"] if isinstance(r["meta"], dict) else (r["meta"] or {}),
                    "ip": r["ip"],
                    "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
        except Exception:
            pass
    items = list(reversed(_load_json(AUDIT_FILE)))
    if action:
        items = [x for x in items if x.get("action") == action]
    if admin_login:
        items = [x for x in items if x.get("adminLogin") == admin_login]
    return items[:limit]
