"""Student profile registration fields + ensure PG columns."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from flask import jsonify, request

log = logging.getLogger("geografia.patch_students_profile")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compose_full_name(last_name: str, first_name: str, patronymic: str, fallback: str = "") -> str:
    parts = [p for p in [last_name.strip(), first_name.strip(), patronymic.strip()] if p]
    if parts:
        return " ".join(parts)
    return (fallback or "").strip()


def _norm_gender(g: str) -> str:
    g = (g or "").strip().lower()
    if g in ("male", "m", "мард", "писар", "boy"):
        return "male"
    if g in ("female", "f", "зан", "духтар", "girl"):
        return "female"
    return g if g in ("male", "female") else ""


def ensure_student_profile_columns() -> None:
    try:
        from db.repo import use_pg
        from db.connection import get_session
        from sqlalchemy import text

        if not use_pg():
            return
        with get_session() as s:
            for col, typ in [
                ("last_name", "TEXT"),
                ("first_name", "TEXT"),
                ("patronymic", "TEXT"),
                ("birth_date", "DATE"),
                ("address", "TEXT"),
                ("teacher_name", "TEXT"),
                ("photo_data", "TEXT"),
                ("gender", "TEXT"),
                ("olympiad_title", "TEXT"),
                ("olympiad_start", "DATE"),
            ]:
                s.execute(text(f"ALTER TABLE students ADD COLUMN IF NOT EXISTS {col} {typ}"))
        log.info("student profile columns ensured")
        print("[boot] students profile columns OK")
    except Exception as e:
        log.warning("ensure student profile columns: %s", e)


def _row_public(r: dict) -> dict:
    full = r.get("fullName") or r.get("full_name") or ""
    gender = r.get("gender") or ""
    oly_start = r.get("olympiadStart") or r.get("olympiad_start") or ""
    if oly_start and hasattr(oly_start, "isoformat"):
        oly_start = oly_start.isoformat()[:10]
    else:
        oly_start = str(oly_start)[:10] if oly_start else ""
    return {
        "id": r.get("id") or r.get("student_code"),
        "fullName": full,
        "lastName": r.get("lastName") or r.get("last_name") or "",
        "firstName": r.get("firstName") or r.get("first_name") or "",
        "patronymic": r.get("patronymic") or "",
        "birthDate": r.get("birthDate") or (str(r.get("birth_date") or "")[:10] if r.get("birth_date") else ""),
        "address": r.get("address") or "",
        "className": r.get("className") or r.get("class_name") or "",
        "school": r.get("school") or r.get("school_name") or "",
        "teacher": r.get("teacher") or r.get("teacher_name") or "",
        "gender": gender,
        "olympiadTitle": r.get("olympiadTitle") or r.get("olympiad_title") or "",
        "olympiadStart": oly_start,
        "hasPhoto": bool(r.get("photo_data") or r.get("photoData") or r.get("hasPhoto")),
        "photoData": r.get("photoData") if r.get("photoData") else None,
        "createdAt": r.get("createdAt"),
        "status": r.get("status") or "active",
    }
