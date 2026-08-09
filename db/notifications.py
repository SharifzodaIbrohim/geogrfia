"""Phase 18 — In-app notifications + optional SMTP email."""
from __future__ import annotations

import os
import smtplib
import uuid
from email.message import EmailMessage
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.repo import use_pg, DATA_DIR, _load_json, _save_json, _utc_now

NOTIF_FILE = DATA_DIR / "notifications.json"


def _smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("NOTIFY_EMAIL_FROM"))


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email or not _smtp_configured():
        return False
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT") or 587)
    user = os.environ.get("SMTP_USER") or ""
    password = os.environ.get("SMTP_PASSWORD") or ""
    from_addr = os.environ["NOTIFY_EMAIL_FROM"]
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            if os.environ.get("SMTP_TLS", "1") != "0":
                smtp.starttls()
                smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        return True
    except Exception:
        return False


def create_notification(
    *,
    title: str,
    body: str = "",
    link: str | None = None,
    user_id: str | None = None,
    audience: str = "admin",  # admin | user | all_admins
    email: str | None = None,
) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "audience": audience,
        "title": title,
        "body": body or "",
        "link": link,
        "isRead": False,
        "createdAt": _utc_now(),
    }
    if use_pg():
        try:
            with get_session() as s:
                s.execute(text(
                    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS audience TEXT DEFAULT 'user'"
                ))
                s.execute(
                    text(
                        "INSERT INTO notifications (id, user_id, title, body, link, is_read) "
                        "VALUES (:id, :uid, :title, :body, :link, false)"
                    ),
                    {
                        "id": item["id"],
                        "uid": user_id,
                        "title": title,
                        "body": body or "",
                        "link": link,
                    },
                )
        except Exception:
            items = _load_json(NOTIF_FILE)
            items.append(item)
            _save_json(NOTIF_FILE, items[-1000:])
    else:
        items = _load_json(NOTIF_FILE)
        items.append(item)
        _save_json(NOTIF_FILE, items[-1000:])

    if email:
        send_email(email, title, body or title)
    # optional broadcast email to NOTIFY_ADMIN_EMAIL
    admin_mail = os.environ.get("NOTIFY_ADMIN_EMAIL")
    if audience in ("admin", "all_admins") and admin_mail and not email:
        send_email(admin_mail, title, body or title)
    return item


def list_notifications(
    *,
    audience: str | None = "admin",
    user_id: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    limit = max(1, min(int(limit or 50), 200))
    if use_pg() and user_id:
        try:
            with get_session() as s:
                q = (
                    "SELECT id::text, title, body, link, is_read, created_at "
                    "FROM notifications WHERE user_id::text = :uid "
                )
                params: dict[str, Any] = {"uid": user_id, "lim": limit}
                if unread_only:
                    q += "AND is_read = false "
                q += "ORDER BY created_at DESC LIMIT :lim"
                rows = s.execute(text(q), params).mappings().all()
                return [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "body": r["body"],
                        "link": r["link"],
                        "isRead": r["is_read"],
                        "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
                    }
                    for r in rows
                ]
        except Exception:
            pass
    items = list(reversed(_load_json(NOTIF_FILE)))
    if audience:
        items = [x for x in items if x.get("audience") in (audience, "all_admins", "all")]
    if user_id:
        items = [x for x in items if x.get("userId") == user_id]
    if unread_only:
        items = [x for x in items if not x.get("isRead")]
    return items[:limit]


def mark_read(notif_id: str) -> bool:
    if use_pg():
        try:
            with get_session() as s:
                res = s.execute(
                    text("UPDATE notifications SET is_read = true WHERE id::text = :id"),
                    {"id": notif_id},
                )
                if res.rowcount:
                    return True
        except Exception:
            pass
    items = _load_json(NOTIF_FILE)
    ok = False
    for n in items:
        if n.get("id") == notif_id:
            n["isRead"] = True
            ok = True
            break
    if ok:
        _save_json(NOTIF_FILE, items)
    return ok


def notify_olympiad_event(kind: str, olympiad: dict) -> None:
    title_map = {
        "created": "Олимпиадаи нав",
        "activated": "Олимпиада фаъол шуд",
        "finished": "Олимпиада анҷом ёфт",
    }
    title = title_map.get(kind, "Огоҳӣ: олимпиада")
    body = f"{olympiad.get('title') or '—'} ({olympiad.get('type') or 'olympiad'})"
    create_notification(
        title=title,
        body=body,
        link="/admin",
        audience="admin",
    )


def notify_result(result: dict) -> None:
    create_notification(
        title="Натиҷаи нав",
        body=(
            f"{result.get('studentName') or result.get('studentId')}: "
            f"{result.get('score')}% — {result.get('status')} "
            f"({result.get('olympiadTitle') or result.get('olympiadId')})"
        ),
        link="/admin",
        audience="admin",
    )
