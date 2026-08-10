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
        return {
            "id": u.get("id") or user_id,
            "email": u.get("email"),
            "name": u.get("name"),
            "picture": u.get("picture") or u.get("avatarUrl"),
            "gender": u.get("gender"),
            "school": u.get("school") or u.get("schoolName"),
            "region": u.get("region"),
            "className": u.get("className") or u.get("class"),
            "rating": int(u.get("rating") or 1200),
            "maxRating": int(u.get("maxRating") or u.get("rating") or 1200),
            "profileComplete": bool(u.get("profileComplete")),
            "kind": "gmail",
        }
    return None


def _row_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row.get("email"),
        "name": row.get("name"),
        "picture": row.get("avatar_url"),
        "googleId": row.get("google_id"),
        "gender": row.get("gender"),
        "school": row.get("school_name"),
        "region": row.get("region"),
        "className": row.get("class_name"),
        "rating": int(row.get("rating") or 1200),
        "maxRating": int(row.get("max_rating") or 1200),
        "profileComplete": bool(row.get("profile_complete")),
        "kind": "gmail",
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "lastLoginAt": row["last_login_at"].isoformat() if row.get("last_login_at") else None,
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
                sets = ["profile_complete = :pc"]
                params = {"id": user_id, "pc": complete}
                if gender is not None:
                    sets.append("gender = :gender"); params["gender"] = gender
                if school is not None:
                    sets.append("school_name = :school"); params["school"] = school
                if region is not None:
                    sets.append("region = :region"); params["region"] = region
                if class_name is not None:
                    sets.append("class_name = :cls"); params["cls"] = class_name
                if name is not None:
                    sets.append("name = :name"); params["name"] = name
                s.execute(text(f"UPDATE users SET {', '.join(sets)} WHERE id::text = :id"), params)
            return get_user_by_id(user_id)
        except Exception:
            pass

    profiles = _json_profiles()
    u = profiles.get(user_id) or {"id": user_id}
    if gender is not None: u["gender"] = gender
    if school is not None: u["school"] = school
    if region is not None: u["region"] = region
    if class_name is not None: u["className"] = class_name
    if name is not None: u["name"] = name
    u["profileComplete"] = complete
    u["rating"] = int(u.get("rating") or 1200)
    u["maxRating"] = int(u.get("maxRating") or u["rating"])
    u["updatedAt"] = _utc_now()
    profiles[user_id] = u
    _save_profiles(profiles)
    return get_user_by_id(user_id)


def list_gmail_users(*, school: str | None = None, region: str | None = None, gender: str | None = None, limit: int = 200) -> list[dict]:
    out: list[dict] = []
    _ensure_pg_columns()
    if use_pg():
        try:
            with get_session() as s:
                rows = s.execute(
                    text(
                        "SELECT id::text, email, name, avatar_url, gender, school_name, region, class_name, "
                        "COALESCE(rating,1200) AS rating, COALESCE(max_rating,1200) AS max_rating, "
                        "COALESCE(profile_complete,false) AS profile_complete "
                        "FROM users WHERE google_id IS NOT NULL OR email ILIKE '%@%' "
                        "ORDER BY COALESCE(last_login_at, created_at) DESC NULLS LAST LIMIT :lim"
                    ),
                    {"lim": limit},
                ).mappings().all()
            for row in rows:
                u = _row_user(row)
                if school and school.lower() not in (u.get("school") or "").lower():
                    continue
                if region and region.lower() not in (u.get("region") or "").lower():
                    continue
                if gender and gender != u.get("gender"):
                    continue
                out.append(u)
            if out:
                return out[:limit]
        except Exception:
            pass
    for u in _json_profiles().values():
        item = {
            "id": u.get("id"),
            "email": u.get("email"),
            "name": u.get("name"),
            "picture": u.get("picture"),
            "gender": u.get("gender"),
            "school": u.get("school") or u.get("schoolName"),
            "region": u.get("region"),
            "className": u.get("className"),
            "rating": int(u.get("rating") or 1200),
            "maxRating": int(u.get("maxRating") or 1200),
            "profileComplete": bool(u.get("profileComplete")),
            "kind": "gmail",
        }
        if school and school.lower() not in (item.get("school") or "").lower():
            continue
        if region and region.lower() not in (item.get("region") or "").lower():
            continue
        if gender and gender != item.get("gender"):
            continue
        out.append(item)
    return out[:limit]


def user_quiz_stats(user_id: str) -> dict:
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
                recent.append({
                    "title": r.get("title"),
                    "score": r.get("score"),
                    "status": r.get("status"),
                    "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                })
        except Exception:
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
                    recent.append({
                        "title": "Супориш",
                        "score": sc,
                        "status": r.get("status"),
                        "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
                    })
            except Exception:
                pass

    if attempts == 0:
        try:
            from pathlib import Path as _P
            import json as _json
            for dd in [_P(__file__).resolve().parent.parent / "data", _P.cwd() / "data", _P("/opt/render/project/src/data")]:
                rp = dd / "results.json"
                if not rp.exists():
                    continue
                try:
                    results = _json.loads(rp.read_text(encoding="utf-8")) or []
                except Exception:
                    continue
                if not isinstance(results, list):
                    continue
                uid = str(user_id)
                for r in results:
                    if not isinstance(r, dict):
                        continue
                    rid = str(r.get("userId") or "")
                    sid = str(r.get("studentId") or r.get("studentCode") or "")
                    if not (rid == uid or sid in ("g:" + uid, "gmail:" + uid) or (uid and sid.endswith(uid[:20]))):
                        continue
                    attempts += 1
                    sc = r.get("score")
                    st = (r.get("status") or "").lower()
                    try:
                        sc_f = float(sc) if sc is not None else None
                    except (TypeError, ValueError):
                        sc_f = None
                    if st == "passed" or (sc_f is not None and sc_f >= 70):
                        passed += 1
                        solved += 1
                    else:
                        failed += 1
                    recent.append({
                        "title": r.get("title") or r.get("olympiadTitle") or "Супориш",
                        "score": sc_f,
                        "status": r.get("status") or ("passed" if sc_f and sc_f >= 70 else "failed"),
                        "finishedAt": r.get("finishedAt") or r.get("submittedAt") or r.get("createdAt"),
                    })
                break
        except Exception:
            pass

    return {
        "attempts": attempts,
        "passed": passed,
        "failed": failed,
        "problemsSolved": solved,
        "contests": attempts,
        "recent": recent[:15],
    }
