"""Map olympiad type=quiz into Phase 8 quiz list/API shape."""
from __future__ import annotations

from db.repo import list_olympiads, find_olympiad


def olympiad_as_quiz(o: dict) -> dict:
    qs = o.get("questions") or []
    duration = o.get("durationSec") or o.get("duration_sec")
    if not duration and o.get("startTime") and o.get("endTime"):
        duration = None  # window only
    return {
        "id": o["id"],
        "title": o.get("title"),
        "description": o.get("description") or "",
        "passScore": o.get("passScore") or 70,
        "timeLimitSec": duration,
        "accessMode": "google",  # Gmail or Student ID
        "schoolName": None,
        "status": "published" if o.get("isActive") else "draft",
        "questionCount": o.get("questionCount") or len(qs),
        "source": "olympiad",
        "type": o.get("type") or "quiz",
        "isActive": bool(o.get("isActive")),
        "windowStatus": o.get("windowStatus"),
        "startTime": o.get("startTime"),
        "endTime": o.get("endTime"),
        "questions": [
            {
                "id": q.get("id", i + 1),
                "text": q.get("text"),
                "options": q.get("options") or [],
            }
            for i, q in enumerate(qs)
        ],
    }


def list_bridged_quizzes(include_inactive: bool = False) -> list[dict]:
    out = []
    for o in list_olympiads():
        if (o.get("type") or "olympiad") != "quiz":
            continue
        if not include_inactive and not o.get("isActive"):
            continue
        out.append(olympiad_as_quiz(o))
    return out


def get_bridged_quiz(quiz_id: str, include_answers: bool = False) -> dict | None:
    o = find_olympiad(quiz_id)
    if not o:
        return None
    if (o.get("type") or "olympiad") != "quiz":
        return None
    item = olympiad_as_quiz(o)
    if include_answers:
        qs = o.get("questions") or []
        item["questions"] = [
            {
                "id": q.get("id", i + 1),
                "text": q.get("text"),
                "options": q.get("options") or [],
                "answer": q.get("answer"),
            }
            for i, q in enumerate(qs)
        ]
    return item
