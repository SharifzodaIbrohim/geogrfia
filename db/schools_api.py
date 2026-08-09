"""Phase 6–7 — Schools CRUD + dashboard aggregates."""
from __future__ import annotations

import uuid

from sqlalchemy import text

from db.connection import get_session
from db.repo import use_pg, DATA_DIR, _load_json, _save_json, _utc_now, list_students, list_olympiads, list_results
from db.repo import is_olympiad_open if False else None  # placeholder avoid


def list_schools() -> list[dict]:
    if use_pg():
        with get_session() as s:
            rows = s.execute(text(
                """
                SELECT sc.id::text, sc.name, sc.location, sc.created_at,
                       COUNT(st.id) AS student_count
                FROM schools sc
                LEFT JOIN students st ON st.school_id = sc.id AND st.status = 'active'
                GROUP BY sc.id
                ORDER BY sc.name
                """
            )).mappings().all()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "location": r["location"],
                    "studentCount": int(r["student_count"] or 0),
                    "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
    path = DATA_DIR / "schools.json"
    schools = _load_json(path)
    students = list_students()
    out = []
    for sc in schools:
        name = sc.get("name", "")
        cnt = sum(1 for st in students if (st.get("school") or "") == name)
        out.append({
            "id": sc.get("id"),
            "name": name,
            "location": sc.get("location"),
            "studentCount": cnt,
            "createdAt": sc.get("createdAt"),
        })
    return out


def create_school(name: str, location: str | None = None) -> dict:
    name = name.strip()
    sid = str(uuid.uuid4())
    created = _utc_now()
    if use_pg():
        with get_session() as s:
            existing = s.execute(
                text("SELECT id::text FROM schools WHERE lower(name) = lower(:n)"), {"n": name}
            ).scalar()
            if existing:
                raise ValueError("exists")
            s.execute(
                text("INSERT INTO schools (id, name, location) VALUES (:id, :n, :loc)"),
                {"id": sid, "n": name, "loc": location or None},
            )
        return {"id": sid, "name": name, "location": location, "studentCount": 0, "createdAt": created}
    path = DATA_DIR / "schools.json"
    schools = _load_json(path)
    if any((s.get("name") or "").lower() == name.lower() for s in schools):
        raise ValueError("exists")
    row = {"id": sid, "name": name, "location": location, "createdAt": created}
    schools.append(row)
    _save_json(path, schools)
    return {"id": sid, "name": name, "location": location, "studentCount": 0, "createdAt": created}


def delete_school(school_id: str) -> bool:
    if use_pg():
        with get_session() as s:
            res = s.execute(text("DELETE FROM schools WHERE id::text = :id"), {"id": school_id})
            return res.rowcount > 0
    path = DATA_DIR / "schools.json"
    schools = _load_json(path)
    new_list = [s for s in schools if s.get("id") != school_id]
    if len(new_list) == len(schools):
        return False
    _save_json(path, new_list)
    return True


def dashboard_stats() -> dict:
    students = list_students()
    olympiads = list_olympiads()
    results = list_results()
    schools = list_schools()

    def is_open(o):
        if not o.get("isActive"):
            return False
        # windowStatus may already be computed by public layer; raw list has isActive
        return bool(o.get("isActive"))

    by_school: dict[str, dict] = {}
    for st in students:
        key = st.get("school") or "—"
        by_school.setdefault(key, {"school": key, "students": 0, "results": 0, "passed": 0})
        by_school[key]["students"] += 1
    for r in results:
        key = r.get("studentSchool") or "—"
        by_school.setdefault(key, {"school": key, "students": 0, "results": 0, "passed": 0})
        by_school[key]["results"] += 1
        if r.get("status") == "passed":
            by_school[key]["passed"] += 1

    scores = [int(r.get("score") or 0) for r in results if r.get("score") is not None]
    avg = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "stats": {
            "students": len(students),
            "schools": len(schools),
            "olympiads": len(olympiads),
            "activeOlympiads": sum(1 for o in olympiads if is_open(o)),
            "results": len(results),
            "passed": sum(1 for r in results if r.get("status") == "passed"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "avgScore": avg,
        },
        "bySchool": sorted(by_school.values(), key=lambda x: -x["students"]),
        "recentResults": sorted(results, key=lambda r: r.get("finishedAt") or "", reverse=True)[:20],
    }
