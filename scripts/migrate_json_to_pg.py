#!/usr/bin/env python3
"""
Migrate existing data/*.json → PostgreSQL.

Usage:
  export DATABASE_URL="postgresql://user:pass@host:5432/geografia"
  python scripts/migrate_json_to_pg.py

Idempotent where possible (skips existing logins / student codes).
Does NOT touch countries JSON (static content stays on disk).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATA = ROOT / "data"
SCHEMA = ROOT / "db" / "schema.sql"


def load_list(name: str) -> list:
    path = DATA / name
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def parse_dt(value):
    if not value:
        return None
    try:
        text_v = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text_v)
    except ValueError:
        return None


def main():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("ERROR: set DATABASE_URL")
        sys.exit(1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(url)
    print("Applying schema.sql …")
    with engine.begin() as conn:
        conn.execute(text(SCHEMA.read_text(encoding="utf-8")))

    Session = sessionmaker(bind=engine)
    session = Session()

    # --- Admins ---
    admins = load_list("admins.json")
    for a in admins:
        login = a.get("login")
        if not login:
            continue
        exists = session.execute(
            text("SELECT 1 FROM admins WHERE login = :l"), {"l": login}
        ).first()
        if exists:
            print(f"  skip admin {login}")
            continue
        aid = a.get("id") or str(uuid.uuid4())
        try:
            uuid.UUID(str(aid))
        except ValueError:
            aid = str(uuid.uuid4())
        session.execute(
            text("""
            INSERT INTO admins (id, login, name, salt, password_hash, role, created_by, created_at)
            VALUES (:id, :login, :name, :salt, :ph, 'super_admin', :cb, COALESCE(:ca, now()))
            ON CONFLICT (login) DO NOTHING
            """),
            {
                "id": aid,
                "login": login,
                "name": a.get("name") or login,
                "salt": a.get("salt") or "",
                "ph": a.get("passwordHash") or "",
                "cb": a.get("createdBy"),
                "ca": parse_dt(a.get("createdAt")),
            },
        )
        print(f"  + admin {login}")

    # --- Users (legacy email) ---
    for u in load_list("users.json"):
        email = (u.get("email") or "").strip().lower()
        if not email:
            continue
        exists = session.execute(
            text("SELECT 1 FROM users WHERE email = :e"), {"e": email}
        ).first()
        if exists:
            print(f"  skip user {email}")
            continue
        uid = u.get("id") or str(uuid.uuid4())
        try:
            uuid.UUID(str(uid))
        except ValueError:
            uid = str(uuid.uuid4())
        session.execute(
            text("""
            INSERT INTO users (id, email, name, salt, password_hash, created_at)
            VALUES (:id, :email, :name, :salt, :ph, COALESCE(:ca, now()))
            ON CONFLICT (email) DO NOTHING
            """),
            {
                "id": uid,
                "email": email,
                "name": u.get("name") or email,
                "salt": u.get("salt"),
                "ph": u.get("passwordHash"),
                "ca": parse_dt(u.get("createdAt")),
            },
        )
        print(f"  + user {email}")

    # --- Schools from student.school text ---
    school_map: dict[str, str] = {}
    students = load_list("students.json")
    for s in students:
        name = (s.get("school") or "").strip()
        if name and name not in school_map:
            row = session.execute(
                text("SELECT id FROM schools WHERE lower(name) = lower(:n)"), {"n": name}
            ).first()
            if row:
                school_map[name] = str(row[0])
            else:
                sid = str(uuid.uuid4())
                session.execute(
                    text("INSERT INTO schools (id, name) VALUES (:id, :n)"),
                    {"id": sid, "n": name},
                )
                school_map[name] = sid
                print(f"  + school {name}")

    # --- Students ---
    for s in students:
        code = str(s.get("id") or "").strip()
        if not code:
            continue
        exists = session.execute(
            text("SELECT 1 FROM students WHERE student_code = :c"), {"c": code}
        ).first()
        if exists:
            print(f"  skip student {code}")
            continue
        school_name = (s.get("school") or "").strip() or None
        school_id = school_map.get(school_name) if school_name else None
        session.execute(
            text("""
            INSERT INTO students
              (id, student_code, full_name, class_name, school_id, school_name, created_by, created_at)
            VALUES
              (:id, :code, :fn, :cl, :sid, :sn, :cb, COALESCE(:ca, now()))
            ON CONFLICT (student_code) DO NOTHING
            """),
            {
                "id": str(uuid.uuid4()),
                "code": code,
                "fn": s.get("fullName") or "",
                "cl": s.get("className") or "",
                "sid": school_id,
                "sn": school_name,
                "cb": s.get("createdBy"),
                "ca": parse_dt(s.get("createdAt")),
            },
        )
        print(f"  + student {code}")

    # --- Olympiads (questions embedded in JSON) ---
    for o in load_list("olympiads.json"):
        oid = o.get("id") or str(uuid.uuid4())
        try:
            uuid.UUID(str(oid))
        except ValueError:
            oid = str(uuid.uuid4())
        exists = session.execute(
            text("SELECT 1 FROM olympiads WHERE id = :id"), {"id": oid}
        ).first()
        if exists:
            print(f"  skip olympiad {o.get('title')}")
            continue
        session.execute(
            text("""
            INSERT INTO olympiads
              (id, title, type, pass_score, start_at, end_at, is_active, status, created_at)
            VALUES
              (:id, :title, :type, :ps, :st, :et, :active, 'published', COALESCE(:ca, now()))
            """),
            {
                "id": oid,
                "title": o.get("title") or "Untitled",
                "type": o.get("type") or "olympiad",
                "ps": int(o.get("passScore") or 70),
                "st": parse_dt(o.get("startTime")),
                "et": parse_dt(o.get("endTime")),
                "active": bool(o.get("isActive")),
                "ca": parse_dt(o.get("createdAt")),
            },
        )
        for i, q in enumerate(o.get("questions") or []):
            qid = str(uuid.uuid4())
            session.execute(
                text("""
                INSERT INTO olympiad_questions (id, olympiad_id, sort_order, text)
                VALUES (:id, :oid, :ord, :text)
                """),
                {"id": qid, "oid": oid, "ord": i, "text": q.get("text") or ""},
            )
            answer = int(q.get("answer") or 0)
            for j, opt in enumerate(q.get("options") or []):
                session.execute(
                    text("""
                    INSERT INTO olympiad_options (id, question_id, sort_order, text, is_correct)
                    VALUES (:id, :qid, :ord, :text, :ok)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "qid": qid,
                        "ord": j,
                        "text": str(opt),
                        "ok": j == answer,
                    },
                )
        print(f"  + olympiad {o.get('title')}")

    # --- Results → attempts ---
    for r in load_list("results.json"):
        student_code = str(r.get("studentId") or "").strip()
        oly_id = r.get("olympiadId")
        if not student_code or not oly_id:
            continue
        stu = session.execute(
            text("SELECT id FROM students WHERE student_code = :c"), {"c": student_code}
        ).first()
        student_uuid = str(stu[0]) if stu else None
        status = r.get("status") or "submitted"
        if status not in ("passed", "failed", "submitted"):
            status = "submitted"
        session.execute(
            text("""
            INSERT INTO attempts
              (id, kind, olympiad_id, student_id, student_name, student_class, student_school,
               score, correct, total, pass_score, status, finished_at, started_at)
            VALUES
              (:id, 'olympiad', :oid, :sid, :sn, :sc, :ss,
               :score, :correct, :total, :ps, :status, :fin, COALESCE(:fin, now()))
            """),
            {
                "id": r.get("id") or str(uuid.uuid4()),
                "oid": oly_id,
                "sid": student_uuid,
                "sn": r.get("studentName"),
                "sc": r.get("studentClass"),
                "ss": r.get("studentSchool"),
                "score": r.get("score"),
                "correct": r.get("correct"),
                "total": r.get("total"),
                "ps": r.get("passScore"),
                "status": status,
                "fin": parse_dt(r.get("finishedAt")),
            },
        )
        print(f"  + result {r.get('studentName')} {r.get('score')}%")

    session.commit()
    session.close()
    print("Migration done.")


if __name__ == "__main__":
    main()
