"""Patch olympiad create/scoring for multi-type questions + showResultsToStudents."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("geografia.patch_olympiad_builder")


def _norm_text(s: Any) -> str:
    return " ".join(str(s or "").strip().split()).lower()


def normalize_question(i: int, q: dict) -> dict:
    qtype = str(q.get("type") or q.get("qtype") or "single").strip().lower()
    if qtype in ("choice", "mcq", "single_choice"):
        qtype = "single"
    if qtype in ("match",):
        qtype = "matching"
    if qtype not in ("single", "short", "matching", "text"):
        qtype = "single"
    text = str(q.get("text", "")).strip()
    if not text:
        raise ValueError(f"question {i+1}: empty text")

    try:
        max_score = float(q.get("maxScore") or q.get("points") or 1)
    except (TypeError, ValueError):
        max_score = 1.0
    if max_score <= 0:
        max_score = 1.0

    if qtype == "single":
        options = q.get("options") or []
        opts_out = []
        for o in options:
            if isinstance(o, dict):
                opts_out.append(str(o.get("text") or o.get("label") or o.get("value") or "").strip())
            else:
                opts_out.append(str(o).strip() if o is not None else "")
        opts_out = [o for o in opts_out if o]
        if len(opts_out) < 2:
            raise ValueError(f"question {i+1}: need >=2 options")
        answer = q.get("answer")
        if answer is None:
            ca = q.get("correctAnswer")
            if isinstance(ca, int):
                answer = ca
            elif isinstance(ca, str) and ca.isdigit():
                answer = int(ca)
            else:
                answer = 0
        try:
            answer = int(answer)
        except (TypeError, ValueError):
            answer = 0
        if answer < 0 or answer >= len(opts_out):
            answer = 0
        return {"id": i + 1, "type": "single", "text": text, "options": opts_out, "answer": answer, "maxScore": max_score}

    if qtype == "short":
        correct = (
            q.get("correctText")
            or q.get("correctAnswer")
            or q.get("answerText")
            or q.get("answer")
            or ""
        )
        correct = str(correct).strip()
        if not correct:
            raise ValueError(f"question {i+1}: short needs correctAnswer")
        return {"id": i + 1, "type": "short", "text": text, "correctText": correct, "maxScore": max_score}

    if qtype == "matching":
        left = q.get("leftItems") or q.get("left") or []
        right = q.get("rightItems") or q.get("right") or []
        pairs = q.get("correctPairs") or q.get("pairs") or q.get("answer") or {}
        if isinstance(left, str):
            left = [x.strip() for x in left.split("\n") if x.strip()]
        if isinstance(right, str):
            right = [x.strip() for x in right.split("\n") if x.strip()]
        if not isinstance(pairs, dict):
            pairs = {}
        pairs = {str(k): int(v) if str(v).lstrip("-").isdigit() else v for k, v in pairs.items()}
        if not left or not right:
            raise ValueError(f"question {i+1}: matching needs left/right items")
        if not pairs:
            raise ValueError(f"question {i+1}: matching needs correctPairs")
        return {
            "id": i + 1,
            "type": "matching",
            "text": text,
            "leftItems": list(left),
            "rightItems": list(right),
            "pairs": pairs,
            "correctPairs": pairs,
            "maxScore": max_score,
        }

    # text
    correct = str(
        q.get("correctText") or q.get("correctAnswer") or q.get("answerText") or q.get("answer") or ""
    ).strip()
    if not correct:
        raise ValueError(f"question {i+1}: text needs correctAnswer keywords")
    return {
        "id": i + 1,
        "type": "text",
        "text": text,
        "correctText": correct,
        "maxScore": max_score,
    }


def install(app=None):
    print("[boot] patch_olympiad_builder: multi-type normalize ready")
    try:
        from db import olympiad_engine as oe
    except Exception as e:
        log.warning("oe import: %s", e)
        return

    # expose normalize for create routes
    try:
        import sys
        mod = sys.modules[__name__]
        if not hasattr(oe, "normalize_question"):
            oe.normalize_question = normalize_question
    except Exception:
        pass

    # Hook create if repo has create_olympiad
    try:
        from db import repo
        _orig = getattr(repo, "create_olympiad", None) or getattr(repo, "save_olympiad", None)
        if callable(_orig):
            def _create(data, *a, **kw):
                qs = (data or {}).get("questions") or []
                if qs:
                    normed = []
                    for i, q in enumerate(qs):
                        if not isinstance(q, dict):
                            continue
                        try:
                            normed.append(normalize_question(i, q))
                        except Exception as e:
                            log.warning("normalize q%d: %s", i, e)
                            raise
                    data = dict(data)
                    data["questions"] = normed
                return _orig(data, *a, **kw)
            if hasattr(repo, "create_olympiad"):
                repo.create_olympiad = _create
            if hasattr(repo, "save_olympiad"):
                repo.save_olympiad = _create
            log.info("patch_olympiad_builder: create hooked")
    except Exception as e:
        log.warning("create hook: %s", e)

    print("[boot] patch_olympiad_builder installed")
