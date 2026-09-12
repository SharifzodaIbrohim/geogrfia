"""Review + grade multi-type: correctText, matching pairs, human-readable answers."""
from __future__ import annotations

import json
import logging

log = logging.getLogger("geografia.patch_review_multitype")


def _nt(v):
    return " ".join(str(v or "").strip().split()).lower()


def _format_matching(student, correct_pairs, left, right):
    left = left or []
    right = right or []
    pairs = correct_pairs if isinstance(correct_pairs, dict) else {}
    stu = student if isinstance(student, dict) else {}
    if isinstance(student, str):
        try:
            stu = json.loads(student)
        except Exception:
            stu = {}
    lines_ok = []
    lines_stu = []
    for k, v in sorted(pairs.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0])):
        try:
            li, ri = int(k), int(v)
        except Exception:
            continue
        L = left[li] if 0 <= li < len(left) else str(li)
        R = right[ri] if 0 <= ri < len(right) else str(ri)
        lines_ok.append(f"{L} → {R}")
    for k, v in sorted(stu.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0])):
        try:
            li, ri = int(k), int(v)
        except Exception:
            lines_stu.append(f"{k} → {v}")
            continue
        L = left[li] if 0 <= li < len(left) else str(li)
        R = right[ri] if 0 <= ri < len(right) else str(ri)
        lines_stu.append(f"{L} → {R}")
    return "; ".join(lines_ok) if lines_ok else "", "; ".join(lines_stu) if lines_stu else str(student or "")


def _grade_item(q, student_raw):
    qtype = str((q or {}).get("type") or "single").lower()
    max_s = 1.0
    try:
        max_s = float((q or {}).get("maxScore") or (q or {}).get("points") or 1) or 1.0
    except Exception:
        max_s = 1.0

    if qtype in ("short", "text", "number", "numeric", "open", "essay"):
        expected = (
            (q or {}).get("correctText")
            or (q or {}).get("correctAnswer")
            or (q or {}).get("answerText")
            or ""
        )
        expected = str(expected).strip()
        got = student_raw
        if isinstance(got, dict):
            got = got.get("t") or got.get("text") or got.get("value") or ""
        got = str(got or "").strip()
        if not got:
            return False, True, 0.0, expected, ""
        ok = False
        if qtype == "text" or "|" in expected:
            keys = [x.strip() for x in expected.split("|") if x.strip()]
            ok = any(_nt(k) in _nt(got) or _nt(got) == _nt(k) for k in keys)
        else:
            ok = _nt(got) == _nt(expected)
        return ok, False, max_s if ok else 0.0, expected, got

    if qtype in ("matching", "match"):
        pairs = (q or {}).get("pairs") or (q or {}).get("correctPairs") or {}
        left = (q or {}).get("leftItems") or (q or {}).get("left") or []
        right = (q or {}).get("rightItems") or (q or {}).get("right") or []
        stu = student_raw
        if isinstance(stu, str):
            try:
                stu = json.loads(stu)
            except Exception:
                stu = {}
        if not isinstance(stu, dict):
            stu = {}
        ok_n = 0
        total_p = len(pairs) or 1
        if isinstance(pairs, dict) and pairs:
            for k, v in pairs.items():
                try:
                    if int(stu.get(str(k), stu.get(k, -999))) == int(v):
                        ok_n += 1
                except Exception:
                    pass
        frac = ok_n / total_p if total_p else 0.0
        ok = frac >= 1.0
        ca, sa = _format_matching(stu, pairs, left, right)
        return ok, (not stu), frac * max_s, ca, sa

    return None, None, None, None, None


def install(app=None):
    try:
        from db import patch_attempt_review as par
    except Exception as e:
        log.warning("review import: %s", e)
        return

    orig = getattr(par, "build_review", None)
    if not callable(orig):
        log.warning("no build_review")
        return

    def build_review(attempt_id, *a, **kw):
        rev = orig(attempt_id, *a, **kw)
        if not isinstance(rev, dict):
            return rev
        oly_qs = []
        try:
            from db.repo import find_olympiad
            oid = rev.get("olympiadId")
            oly = find_olympiad(oid) if oid else None
            if isinstance(oly, dict):
                oly_qs = oly.get("questions") or []
        except Exception as e:
            log.warning("find oly for review: %s", e)

        by_id = {}
        by_text = {}
        for i, q in enumerate(oly_qs):
            if not isinstance(q, dict):
                continue
            by_id[str(q.get("id"))] = q
            by_id[str(i)] = q
            by_id[str(i + 1)] = q
            by_text[_nt(q.get("text"))] = q

        items = rev.get("items") or []
        ok_n = blank_n = bad_n = 0
        earned = 0.0
        total_max = 0.0
        new_items = []
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                new_items.append(it)
                continue
            it = dict(it)
            q = (
                by_id.get(str(it.get("questionId") or ""))
                or by_text.get(_nt(it.get("question") or it.get("text")))
                or (oly_qs[i] if i < len(oly_qs) else None)
                or {}
            )
            if q.get("type"):
                it["type"] = q.get("type")
            student_raw = it.get("studentAnswer")
            graded = _grade_item(q, student_raw)
            if graded[0] is not None:
                ok, is_blank, pts, ca, sa = graded
                try:
                    ms = float(q.get("maxScore") or it.get("maxScore") or 1) or 1.0
                except Exception:
                    ms = 1.0
                total_max += ms
                it["correctAnswer"] = ca
                it["studentAnswer"] = sa if sa is not None else it.get("studentAnswer")
                it["isCorrect"] = bool(ok) and not is_blank
                it["isBlank"] = bool(is_blank)
                it["points"] = pts
                it["maxScore"] = ms
                if is_blank:
                    it["resultLabel"] = "Беҷавоб"
                    blank_n += 1
                elif ok:
                    it["resultLabel"] = "Дуруст"
                    ok_n += 1
                    earned += pts
                else:
                    it["resultLabel"] = "Нодуруст"
                    bad_n += 1
            else:
                try:
                    ms = float(it.get("maxScore") or 1) or 1.0
                except Exception:
                    ms = 1.0
                total_max += ms
                if it.get("isBlank"):
                    blank_n += 1
                elif it.get("isCorrect"):
                    ok_n += 1
                    earned += ms
                    it["points"] = ms
                else:
                    bad_n += 1
                    if not it.get("correctAnswer"):
                        ca = q.get("correctText") or q.get("correctAnswer")
                        if ca is not None:
                            it["correctAnswer"] = str(ca)
            new_items.append(it)

        rev["items"] = new_items
        total = len(new_items) or 1
        if total_max <= 0:
            total_max = float(total)
        score = int(round(100.0 * earned / total_max)) if total_max else 0
        rev["correct"] = ok_n
        rev["earned"] = earned
        rev["total"] = total
        rev["totalMax"] = total_max
        rev["score"] = score
        rev["stats"] = {"correct": ok_n, "wrong": bad_n, "blank": blank_n, "total": total}

        try:
            if score > 0:
                from sqlalchemy import text
                from db.connection import get_session
                with get_session() as s:
                    s.execute(
                        text(
                            "UPDATE attempts SET score=:s, correct=:c, total=:t WHERE id::text=:id"
                        ),
                        {"s": score, "c": ok_n, "t": total, "id": str(attempt_id)},
                    )
        except Exception as e:
            log.warning("review score writeback: %s", e)

        return rev

    par.build_review = build_review
    if hasattr(par, "_correct"):
        _orig_c = par._correct

        def _correct(q, texts):
            for k in ("correctText", "correctAnswer", "answerText", "correct"):
                v = (q or {}).get(k)
                if v is not None and not isinstance(v, (list, dict)):
                    vs = str(v).strip()
                    if vs:
                        return vs
            return _orig_c(q, texts)

        par._correct = _correct

    print("[boot] patch_review_multitype: short/matching regrade + display")
    log.info("patch_review_multitype installed")
