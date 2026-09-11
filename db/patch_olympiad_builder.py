"""Patch olympiad create/scoring for multi-type questions + showResultsToStudents."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("geografia.patch_olympiad_builder")


def _norm_text(v: Any) -> str:
    return " ".join(str(v or "").strip().lower().split())


def normalize_question(i: int, q: dict) -> dict:
    if not isinstance(q, dict):
        q = {"text": str(q)}
    qtype = str(q.get("type") or "single").lower().strip()
    if qtype in ("choice", "mcq", "select"):
        qtype = "single"
    if qtype in ("match",):
        qtype = "matching"
    if qtype not in ("single", "short", "matching", "text"):
        qtype = "single"
    text = str(q.get("text") or q.get("question") or "").strip()
    try:
        max_score = float(q.get("maxScore", 1))
    except (TypeError, ValueError):
        max_score = 1.0
    if max_score < 0.5:
        max_score = 0.5

    if qtype == "single":
        options = []
        for o in q.get("options") or q.get("choices") or []:
            if isinstance(o, dict):
                options.append(str(o.get("text") or o.get("label") or o))
            else:
                options.append(str(o))
        answer = q.get("answer")
        if answer is None:
            answer = q.get("correctIndex", q.get("correct_index"))
        try:
            answer = int(answer)
        except (TypeError, ValueError):
            if answer is not None:
                want = str(answer).strip().lower()
                for j, o in enumerate(options):
                    if o.strip().lower() == want:
                        answer = j
                        break
        return {"id": i + 1, "type": "single", "text": text, "options": options, "answer": answer, "maxScore": max_score}

    if qtype == "short":
        correct = (
            q.get("correctText")
            or q.get("correctAnswer")
            or q.get("answerText")
            or (q.get("answer") if not isinstance(q.get("answer"), (list, dict)) else None)
            or ""
        )
        correct = str(correct).strip()
        return {"id": i + 1, "type": "short", "text": text, "correctText": correct, "maxScore": max_score}

    if qtype == "matching":
        left = [str(x).strip() for x in (q.get("leftItems") or q.get("left") or []) if str(x).strip()]
        right = [str(x).strip() for x in (q.get("rightItems") or q.get("right") or []) if str(x).strip()]
        if len(left) < 2:
            left = left + [""] * (2 - len(left))
        pairs_raw = q.get("pairs") or q.get("correctPairs") or q.get("answer") or {}
        pairs: dict[str, int] = {}
        if isinstance(pairs_raw, dict):
            for k, v in pairs_raw.items():
                try:
                    pairs[str(int(k))] = int(v)
                except (TypeError, ValueError):
                    pass
        # Auto identity 1→1, 2→2 when empty
        if not pairs:
            for i0 in range(len(left)):
                pairs[str(i0)] = i0
        if not pairs:
            pairs = {"0": 0}
        try:
            ms = float(q.get("maxScore", len(pairs) or len(left) or 1))
        except (TypeError, ValueError):
            ms = float(len(pairs) or len(left) or 1)
        if ms < 0.5:
            ms = float(len(pairs) or 1)
        return {
            "id": i + 1,
            "type": "matching",
            "text": text,
            "leftItems": left,
            "rightItems": right,
            "pairs": pairs,
            "pairsText": str(q.get("pairsText") or ""),
            "maxScore": ms,
        }

    # text
    correct = (
        q.get("correctText")
        or q.get("correctAnswer")
        or q.get("answerText")
        or (q.get("answer") if not isinstance(q.get("answer"), (list, dict)) else None)
        or ""
    )
    return {
        "id": i + 1,
        "type": "text",
        "text": text,
        "correctText": str(correct or "").strip(),
        "maxScore": max_score,
        "manual": not bool(str(correct or "").strip()),
    }


def score_question(q: dict, selected: Any) -> tuple[float, float]:
    """Return (earned, max_score). Matching = partial credit per pair."""
    if not isinstance(q, dict):
        return 0.0, 1.0
    qtype = str(q.get("type") or "single").lower()
    try:
        max_s = float(q.get("maxScore") or 1)
    except (TypeError, ValueError):
        max_s = 1.0
    if max_s < 0.5:
        max_s = 1.0

    if qtype == "single":
        try:
            ans = int(q.get("answer"))
        except (TypeError, ValueError):
            ans = None
        try:
            sel = int(selected)
        except (TypeError, ValueError):
            # text selected vs options
            opts = q.get("options") or []
            sel = None
            if selected is not None:
                want = str(selected).strip().lower()
                for j, o in enumerate(opts):
                    if str(o).strip().lower() == want:
                        sel = j
                        break
        return (max_s if ans is not None and sel is not None and sel == ans else 0.0), max_s

    if qtype == "short":
        want = _norm_text(q.get("correctText"))
        got = _norm_text(selected)
        return (max_s if want and got == want else 0.0), max_s

    if qtype == "matching":
        pairs = q.get("pairs") or {}
        left = q.get("leftItems") or q.get("left") or []
        right = q.get("rightItems") or q.get("right") or []
        if not pairs and left:
            pairs = {str(i): i for i in range(len(left))}
        total = len(pairs) or len(left) or 1
        ok = 0
        if isinstance(selected, dict):
            for k, v in pairs.items():
                got = selected.get(str(k), selected.get(k))
                if got is None:
                    continue
                try:
                    if int(got) == int(v):
                        ok += 1
                        continue
                except (TypeError, ValueError):
                    pass
                try:
                    want = str(right[int(v)]).strip().lower() if right and int(v) < len(right) else str(v).strip().lower()
                    if str(got).strip().lower() == want:
                        ok += 1
                except Exception:
                    if str(got).strip().lower() == str(v).strip().lower():
                        ok += 1
        # Partial: each correct pair earns max_s/total (4 pts / 4 pairs = 1 each)
        return ((ok / total) * max_s if total else 0.0), max_s

    if qtype == "text":
        keys = [x.strip() for x in str(q.get("correctText") or "").split("|") if x.strip()]
        if not keys:
            return 0.0, max_s
        got = _norm_text(selected)
        if any(_norm_text(k) in got for k in keys):
            return max_s, max_s
        return 0.0, max_s
    return 0.0, max_s


def install(app=None):
    try:
        import db.olympiad_engine as eng
    except Exception as e:
        log.warning("engine import: %s", e)
        eng = None

    if eng is not None:
        try:
            eng.score_question = score_question  # type: ignore
            eng.normalize_question = normalize_question  # type: ignore
        except Exception as e:
            log.warning("engine patch: %s", e)

    if app is None:
        print("[boot] patch_olympiad_builder: helpers only")
        return

    print("[boot] patch_olympiad_builder: multi-type + maxScore + matching partial")
