"""P1.10 — Ensure public quiz/olympiad payloads never include is_correct / answer."""
from __future__ import annotations

_FORBIDDEN = {
    "answer", "correct", "correctIndex", "correct_index",
    "is_correct", "isCorrect", "solution", "explanation",
}


def sanitize_options(options) -> list[str]:
    out = []
    for o in options or []:
        if isinstance(o, dict):
            out.append(str(o.get("text") or o.get("label") or ""))
        else:
            out.append(str(o))
    return out


def sanitize_question(q: dict) -> dict:
    return {
        "id": q.get("id"),
        "text": q.get("text"),
        "options": sanitize_options(q.get("options")),
        **({"originalIndex": q["originalIndex"]} if "originalIndex" in q else {}),
    }


def sanitize_quiz_payload(quiz: dict | None) -> dict | None:
    if not quiz:
        return quiz
    q = dict(quiz)
    q["questions"] = [sanitize_question(item) for item in (q.get("questions") or [])]
    for k in list(q.keys()):
        if k in _FORBIDDEN:
            q.pop(k, None)
    return q
