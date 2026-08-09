"""Phase 13–16 — monitoring, filtered results, leaderboard, CSV export."""
from __future__ import annotations

import csv
import io
from typing import Any

from db.repo import list_results, list_olympiads, list_students, find_olympiad
from db import olympiad_engine


def live_monitor() -> dict:
    olympiads = list_olympiads()
    results = list_results()
    sessions = olympiad_engine._load_sessions()

    active = []
    finished = []
    for o in olympiads:
        oid = o.get("id")
        o_results = [r for r in results if r.get("olympiadId") == oid]
        in_prog = [
            s for s in sessions
            if s.get("olympiadId") == oid and s.get("status") == "in_progress"
        ]
        row = {
            "id": oid,
            "title": o.get("title"),
            "type": o.get("type"),
            "isActive": o.get("isActive"),
            "windowStatus": o.get("windowStatus"),
            "finishedCount": len(o_results),
            "inProgressCount": len(in_prog),
            "passed": sum(1 for r in o_results if r.get("status") == "passed"),
            "failed": sum(1 for r in o_results if r.get("status") == "failed"),
        }
        if o.get("isActive") or in_prog:
            active.append(row)
        if o_results:
            finished.append(row)

    progress = []
    for s in sessions:
        if s.get("status") != "in_progress":
            continue
        ans = s.get("answers") or {}
        progress.append({
            "sessionId": s.get("id"),
            "olympiadId": s.get("olympiadId"),
            "studentCode": s.get("studentCode"),
            "studentName": s.get("studentName"),
            "startedAt": s.get("startedAt"),
            "endsAt": s.get("endsAt"),
            "answered": len(ans),
            "savedCount": len(ans),
        })

    return {
        "active": active,
        "finished": finished,
        "inProgress": progress,
        "stats": {
            "olympiads": len(olympiads),
            "activeOlympiads": sum(1 for o in olympiads if o.get("isActive")),
            "results": len(results),
            "inProgressSessions": len(progress),
            "students": len(list_students()),
        },
    }


def filter_results(
    *,
    olympiad_id: str | None = None,
    school: str | None = None,
    class_name: str | None = None,
    status: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
) -> list[dict]:
    rows = list_results(olympiad_id) if olympiad_id else list_results()
    out = []
    for r in rows:
        if school and (r.get("studentSchool") or "").lower() != school.lower():
            continue
        if class_name and (r.get("studentClass") or "").lower() != class_name.lower():
            continue
        if status and r.get("status") != status:
            continue
        sc = r.get("score")
        try:
            sc_i = int(sc) if sc is not None else None
        except (TypeError, ValueError):
            sc_i = None
        if min_score is not None and (sc_i is None or sc_i < min_score):
            continue
        if max_score is not None and (sc_i is None or sc_i > max_score):
            continue
        out.append(r)
    out.sort(key=lambda x: (-(x.get("score") or 0), x.get("finishedAt") or ""))
    return out


def leaderboard(
    olympiad_id: str,
    *,
    limit: int = 50,
    school: str | None = None,
) -> dict:
    o = find_olympiad(olympiad_id)
    if not o:
        raise ValueError("not_found")
    # public if leaderboardPublic true or default True for finished
    public = o.get("leaderboardPublic")
    if public is None:
        public = True
    rows = filter_results(olympiad_id=olympiad_id, school=school)
    board = []
    for i, r in enumerate(rows[: max(1, min(limit, 200))], start=1):
        board.append({
            "rank": i,
            "studentName": r.get("studentName"),
            "studentClass": r.get("studentClass"),
            "studentSchool": r.get("studentSchool"),
            "score": r.get("score"),
            "status": r.get("status"),
            "finishedAt": r.get("finishedAt"),
        })
    return {
        "olympiadId": olympiad_id,
        "title": o.get("title"),
        "leaderboardPublic": bool(public),
        "entries": board,
        "total": len(rows),
    }


def set_leaderboard_public(olympiad_id: str, is_public: bool) -> dict | None:
    from db import repo

    if not repo.use_pg():
        items = repo._load_json(repo.OLYMPIADS_FILE)
        for o in items:
            if o.get("id") == olympiad_id:
                o["leaderboardPublic"] = bool(is_public)
                repo._save_json(repo.OLYMPIADS_FILE, items)
                return o
        return None
    # PG: store in questions JSON sidecar is heavy; use results-only flag via olympiads update
    o = find_olympiad(olympiad_id)
    if not o:
        return None
    # try duration-style column
    try:
        from db.connection import get_session
        from sqlalchemy import text

        with get_session() as s:
            s.execute(text(
                "ALTER TABLE olympiads ADD COLUMN IF NOT EXISTS leaderboard_public BOOLEAN DEFAULT TRUE"
            ))
            s.execute(
                text("UPDATE olympiads SET leaderboard_public = :p WHERE id::text = :id"),
                {"p": bool(is_public), "id": olympiad_id},
            )
    except Exception:
        pass
    o["leaderboardPublic"] = bool(is_public)
    return o


def results_csv(
    *,
    olympiad_id: str | None = None,
    school: str | None = None,
    class_name: str | None = None,
    status: str | None = None,
) -> str:
    rows = filter_results(
        olympiad_id=olympiad_id,
        school=school,
        class_name=class_name,
        status=status,
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([
        "student_id", "name", "class", "school",
        "olympiad", "score", "correct", "total", "status", "finished_at",
    ])
    for r in rows:
        w.writerow([
            r.get("studentId"),
            r.get("studentName"),
            r.get("studentClass"),
            r.get("studentSchool"),
            r.get("olympiadTitle") or r.get("olympiadId"),
            r.get("score"),
            r.get("correct"),
            r.get("total"),
            r.get("status"),
            r.get("finishedAt"),
        ])
    return buf.getvalue()
