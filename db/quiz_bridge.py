"""Map olympiad events into Phase 8 quiz list/API shape.

Public /quiz rules (P0.3 fix):
  - type=olympiad  → NEVER listed on public /api/quizzes (Student portal / assigned only)
  - type=quiz      → may appear on /quiz, but start requires Student ID (no Gmail open)
  - Admin list can still see all via list_bridged_quizzes(include_inactive=True, for_admin=True)
"""
from __future__ import annotations

from db.repo import list_olympiads, find_olympiad


def _event_type(o: dict) -> str:
    return (o.get("type") or "olympiad").lower()


def olympiad_as_quiz(o: dict) -> dict:
    """Public shape — never include answer keys."""
    qs = o.get("questions") or []
    duration = o.get("durationSec") or o.get("duration_sec")
    if not duration and o.get("startTime") and o.get("endTime"):
        duration = None
    oly_type = _event_type(o)
    if oly_type == "olympiad":
        access_mode = "olympiad"
    else:
        access_mode = "school"  # Student ID; not google
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
    Public /quiz never lists any olympiad-sourced events (hard empty list).
    Admin: for_admin=True, public_only=False → full list.
    """
    if public_only and not for_admin:
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
