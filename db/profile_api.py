"""User profile (Google/public users) + stats for Profile page and admin monitor."""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text

from db.connection import get_session
from db.repo import use_pg, DATA_DIR, _load_json, _save_json, _utc_now

USERS_EXTRA = DATA_DIR / "user_profiles.json"


def _ensure_pg_columns() -> None:
    if not use_pg():
        return
    alters = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS gender TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS school_name TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS region TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS class_name TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS rating INT DEFAULT 1200",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_rating INT DEFAULT 1200",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_complete BOOLEAN DEFAULT false",
    ]
    try:
        with get_session() as s:
            for a in alters:
                try:
                    s.execute(text(a))
                except Exception:
                    pass
    except Exception:
        pass


def _json_profiles() -> dict:
    data = _load_json(USERS_EXTRA)
    if isinstance(data, list):
        # migrate list -> dict by id
        out = {}
        for u in data:
            if u.get("id"):
                out[u["id"]] = u
        return out
    return data if isinstance(data, dict) else {}


def _save_profiles(d: dict) -> None:
    _save_json(USERS_EXTRA, d)


def get_user_by_id(user_id: str) -> dict | None:
    if not user_id:
        return None
    _ensure_pg_columns()
    if use_pg():
        try:
            with get_session() as s:
                row = s.execute(
                    text(
                        "SELECT id::text, email, name, avatar_url, google_id, "
                        "gender, school_name, region, class_name, "
                        "COALESCE(rating,1200) AS rating, COALESCE(max_rating,1200) AS max_rating, "
                        "COALESCE(profile_complete,false) AS profile_complete, "
                        "created_at, last_login_at "
                        "FROM users WHERE id::text = :id"
                    ),
                    {"id": user_id},
                ).mappings().first()
            if row:
                return _row_user(row)
        except Exception:
            pass
    profiles = _json_profiles()
    u = profiles.get(user_id)
    if u:
        return dict(u)
    # fallback: try data/users.json if exists
    users = _load_json(DATA_DIR / "users.json")
    if isinstance(users, list):
        for x in users:
            if str(x.get("id")) == str(user_id):
                p = profiles.get(user_id) or {}
                return {**x, **p}
    return None


def _row_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "picture": row.get("avatar_url"),
        "avatarUrl": row.get("avatar_url"),
        "googleId": row.get("google_id"),
        "gender": row.get("gender"),
        "school": row.get("school_name"),
        "region": row.get("region"),
        "className": row.get("class_name"),
        "rating": int(row.get("rating") or 1200),
        "maxRating": int(row.get("max_rating") or 1200),
        "profileComplete": bool(row.get("profile_complete")),
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "lastLoginAt": row["last_login_at"].isoformat() if row.get("last_login_at") else None,
        "kind": "gmail",
    }


def update_profile(user_id: str, payload: dict) -> dict | None:
    gender = str(payload.get("gender") or "").strip().lower()
    if gender in ("male", "boy", "писар", "m"):
        gender = "male"
    elif gender in ("female", "girl", "духтар", "f"):
        gender = "female"
    else:
        gender = gender or None

    school = str(payload.get("school") or payload.get("schoolName") or "").strip() or None
    region = str(payload.get("region") or payload.get("city") or "").strip() or None
    class_name = str(payload.get("className") or payload.get("class") or "").strip() or None
    name = str(payload.get("name") or "").strip() or None

    complete = bool(gender and school and region and class_name)

    _ensure_pg_columns()
    if use_pg():
        try:
            with get_session() as s:
                s.execute(
                    text(
                        "UPDATE users SET "
                        "gender = COALESCE(:gender, gender), "
                        "school_name = COALESCE(:school, school_name), "
                        "region = COALESCE(:region, region), "
                        "class_name = COALESCE(:cls, class_name), "
                        "name = COALESCE(:name, name), "
                        "profile_complete = :complete "
                        "WHERE id::text = :id"
                    ),
                    {
                        "id": user_id,
                        "gender": gender,
                        "school": school,
                        "region": region,
                        "cls": class_name,
                        "name": name,
                        "complete": complete,
                    },
                )
            return get_user_by_id(user_id)
        except Exception:
            pass

    profiles = _json_profiles()
    base = profiles.get(user_id) or {"id": user_id}
    if gender:
        base["gender"] = gender
    if school:
        base["school"] = school
    if region:
        base["region"] = region
    if class_name:
        base["className"] = class_name
    if name:
        base["name"] = name
    base["profileComplete"] = complete
    base["kind"] = "gmail"
    base["updatedAt"] = _utc_now()
    profiles[user_id] = base
    _save_profiles(profiles)
    full = get_user_by_id(user_id) or base
    full.update(base)
    return full


def list_gmail_users(
    *,
    school: str | None = None,
    region: str | None = None,
    gender: str | None = None,
    limit: int = 200,
) -> list[dict]:
    _ensure_pg_columns()
    limit = max(1, min(int(limit or 200), 500))
    if use_pg():
        try:
            q = (
                "SELECT id::text, email, name, avatar_url, gender, school_name, region, class_name, "
                "COALESCE(rating,1200) AS rating, COALESCE(max_rating,1200) AS max_rating, "
                "COALESCE(profile_complete,false) AS profile_complete, created_at, last_login_at "
                "FROM users WHERE google_id IS NOT NULL "
            )
            params: dict[str, Any] = {"lim": limit}
            if school:
                q += "AND school_name ILIKE :school "
                params["school"] = f"%{school}%"
            if region:
                q += "AND region ILIKE :region "
                params["region"] = f"%{region}%"
            if gender:
                q += "AND gender = :gender "
                params["gender"] = gender
            q += "ORDER BY created_at DESC LIMIT :lim"
            with get_session() as s:
                rows = s.execute(text(q), params).mappings().all()
            return [_row_user(r) for r in rows]
        except Exception:
            pass
    profiles = _json_profiles()
    items = list(profiles.values())
    if school:
        items = [x for x in items if school.lower() in str(x.get("school") or "").lower()]
    if region:
        items = [x for x in items if region.lower() in str(x.get("region") or "").lower()]
    if gender:
        items = [x for x in items if x.get("gender") == gender]
    return items[:limit]


def user_quiz_stats(user_id: str) -> dict:
    """Attempts/results linked to this user (gmail path)."""
    solved = 0
    attempts = 0
    passed = 0
    failed = 0
    recent: list[dict] = []
    if use_pg():
        try:
            with get_session() as s:
                rows = s.execute(
                    text(
                        "SELECT a.id::text, a.score, a.status, a.finished_at, "
                        "COALESCE(o.title, q.title, 'Quiz') AS title "
                        "FROM attempts a "
                        "LEFT JOIN olympiads o ON o.id = a.olympiad_id "
                        "LEFT JOIN quizzes q ON q.id = a.quiz_id "
                        "WHERE a.user_id::text = :uid AND a.finished_at IS NOT NULL "
                        "ORDER BY a.finished_at DESC LIMIT 50"
                    ),
                    {"uid": user_id},
                ).mappings().all()
            attempts = len(rows)
            for r in rows:
                sc = r.get("score")
                st = (r.get("status") or "").lower()
                if st == "passed" or (sc is not None and float(sc) >= 70):
                    passed += 1
                    solved += 1
                else:
                    failed += 1
                recent.append(
                    {
                        "title": r.get("title"),
                        "score": r.get("score"),
                        "status": r.get("status"),
                        "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                    }
                )
        except Exception:
            # softer query without joins
            try:
                with get_session() as s:
                    rows = s.execute(
                        text(
                            "SELECT score, status, finished_at FROM attempts "
                            "WHERE user_id::text = :uid AND finished_at IS NOT NULL "
                            "ORDER BY finished_at DESC LIMIT 50"
                        ),
                        {"uid": user_id},
                    ).mappings().all()
                attempts = len(rows)
                for r in rows:
                    st = (r.get("status") or "").lower()
                    sc = r.get("score")
                    if st == "passed" or (sc is not None and float(sc) >= 70):
                        passed += 1
                        solved += 1
                    else:
                        failed += 1
                    recent.append(
                        {
                            "title": "Супориш",
                            "score": sc,
                            "status": r.get("status"),
                            "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                        }
                    )
            except Exception:
                pass
    return {
        "attempts": attempts,
        "passed": passed,
        "failed": failed,
        "problemsSolved": solved,
        "recent": recent[:15],
    }
