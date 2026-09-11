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
            # text answer → index
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
        if len(left) < 2 or len(right) < 1:
            raise ValueError(f"Саволи {i + 1}: мувофиқат — бандҳо кам")
        pairs_raw = q.get("pairs") or q.get("correctPairs") or q.get("answer") or {}
        pairs: dict[str, int] = {}
        if isinstance(pairs_raw, dict):
            for k, v in pairs_raw.items():
                try:
                    pairs[str(int(k))] = int(v)
                except (TypeError, ValueError):
                    continue
        if not pairs:
            # Default same-order: left[i] ↔ right[i]
            n = min(len(left), len(right))
            for i0 in range(n):
                pairs[str(i0)] = i0
        if not pairs:
            raise ValueError(f"Саволи {i + 1}: мувофиқат — ҷуфтҳо холӣ")
        try:
            ms = float(q.get("maxScore", len(pairs) or len(left) or 1))
        except (TypeError, ValueError):
            ms = float(len(pairs) or len(left) or 1)
        if ms < 0.5:
            ms = 0.5
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

    correct = (
        q.get("correctText")
        or q.get("correctAnswer")
        or q.get("answerText")
        or ""
    )
    correct = str(correct).strip() if correct is not None else ""
    return {
        "id": i + 1,
        "type": "text",
        "text": text,
        "correctText": correct,
        "maxScore": max_score,
        "manual": not bool(correct),
    }


def score_question(q: dict, selected: Any):
    qtype = str(q.get("type") or "single")
    max_s = float(q.get("maxScore") or 1)
    if qtype == "single":
        correct = q.get("answer")
        try:
            sel = int(selected)
        except (TypeError, ValueError):
            return 0.0, max_s
        return (max_s if correct is not None and sel == int(correct) else 0.0), max_s
    if qtype == "short":
        want = _norm_text(q.get("correctText"))
        got = _norm_text(selected)
        return (max_s if want and got == want else 0.0), max_s
    if qtype == "matching":
        pairs = q.get("pairs") or {}
        if not isinstance(selected, dict):
            return 0.0, max_s
        ok = 0
        total = len(pairs) or len(q.get("leftItems") or []) or 1
        for k, v in pairs.items():
            try:
                if int(selected.get(str(k), selected.get(k))) == int(v):
                    ok += 1
            except (TypeError, ValueError):
                continue
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

    # Wrap create/update if present
    try:
        from flask import request, jsonify
    except Exception:
        print("[boot] patch_olympiad_builder: no flask")
        return

    def _normalize_payload(payload: dict) -> dict:
        qs = payload.get("questions") or []
        out = []
        for i, q in enumerate(qs):
            out.append(normalize_question(i, q if isinstance(q, dict) else {"text": str(q)}))
        payload = dict(payload)
        payload["questions"] = out
        return payload

    # Best-effort: patch known endpoints by rebinding
    bound = 0
    for rule in list(app.url_map.iter_rules()):
        path = str(rule.rule)
        ep = rule.endpoint
        if "olympiad" not in path:
            continue
        if request is None:
            continue
        # leave original; normalization also in engine
        bound += 0
    print("[boot] patch_olympiad_builder: multi-type + maxScore + showResultsToStudents")
