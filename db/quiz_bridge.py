"""Map olympiad events into Phase 8 quiz list/API shape.

Public /api/quizzes must NEVER list olympiad-sourced events.
Student portal uses /api/olympiads/active for olympiads.
Admin can still see bridges via list_bridged_quizzes(include_inactive=True).
"""
from __future__ import annotations

from db.repo import list_olympiads, find_olympiad


def _event_type(o: dict) -> str:
    return (o.get("type") or "olympiad").lower()


def olympiad_as_quiz(o: dict) -> dict:
    qs = o.get("questions") or []
    duration = o.get("durationSec") or o.get("duration_sec")
    if not duration and o.get("startTime") and o.get("endTime"):
        duration = None
    oly_type = _event_type(o)
    access_mode = "olympiad" if oly_type == "olympiad" else "school"
    return {
        "id": o["id"],
        "title": o.get("title"),
        "description": o.get("description") or "",
        "passScore": o.get("passScore") or 70,
        "timeLimitSec": duration,
        "accessMode": access_mode,
        "schoolName": None,
        "status": "published" if o.get("isActive") else "draft",
        "questionCount": o.get("questionCount") or len(qs),
        "source": "olympiad",
        "type": oly_type,
        "isActive": bool(o.get("isActive")),
        "windowStatus": o.get("windowStatus"),
        "startTime": o.get("startTime"),
        "endTime": o.get("endTime"),
        "questions": [
            {
                "id": q.get("id", i + 1),
                "text": q.get("text"),
                "options": list(q.get("options") or []),
            }
            for i, q in enumerate(qs)
        ],
    }


def list_bridged_quizzes(
    include_inactive: bool = False,
    *,
    for_admin: bool = False,
    public_only: bool = True,
) -> list[dict]:
    """
    Public (include_inactive=False, for_admin=False): always [].
    Admin (include_inactive=True or for_admin=True): full list.
    """
    # Public /api/quizzes calls list_bridged_quizzes(include_inactive=False)
    # → never expose olympiads to ordinary users on /quiz
    if not for_admin and not include_inactive:
        return []

    out = []
    for o in list_olympiads():
        if not include_inactive and not o.get("isActive"):
            continue
        out.append(olympiad_as_quiz(o))
    return out


def get_bridged_quiz(quiz_id: str, include_answers: bool = False) -> dict | None:
    o = find_olympiad(quiz_id)
    if not o:
        return None
    item = olympiad_as_quiz(o)
    if include_answers:
        qs = o.get("questions") or []
        item["questions"] = [
            {
                "id": q.get("id", i + 1),
                "text": q.get("text"),
                "options": list(q.get("options") or []),
                "answer": q.get("answer"),
            }
            for i, q in enumerate(qs)
        ]
    return item
