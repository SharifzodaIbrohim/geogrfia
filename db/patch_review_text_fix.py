"""Boot patch: Review text keyword | matching + human-readable pairs."""
from __future__ import annotations
import logging

log = logging.getLogger("geografia.patch_review_text_fix")


def install(app=None):
    try:
        import db.patch_attempt_review as par
    except Exception:
        try:
            import patch_attempt_review as par  # type: ignore
        except Exception as e:
            log.warning("patch_attempt_review import: %s", e)
            return

    def _norm(v):
        return " ".join(str(v or "").strip().split()).lower()

    _orig_grade = getattr(par, "_grade_item", None)
    _orig_build = getattr(par, "build_review", None)

    def _grade_item(qtype, q_orig, sel_info, meta=None):
        if sel_info.get("text") is None and sel_info.get("index") is None and sel_info.get("raw") is None:
            return False
        qtype = (qtype or "single").lower()
        meta = meta or {}
        if qtype in ("short", "text", "number", "numeric", "open", "essay", "written"):
            expected = (
                meta.get("answer")
                or meta.get("correctText")
                or (q_orig or {}).get("answer")
                or (q_orig or {}).get("correctText")
                or (q_orig or {}).get("correctAnswer")
            )
            if expected is None:
                return False
            got = _norm(sel_info.get("text") or sel_info.get("raw"))
            if qtype == "text" or "|" in str(expected):
                keys = [x.strip() for x in str(expected).split("|") if x.strip()]
                return any(_norm(k) == got or _norm(k) in got or got in _norm(k) for k in keys)
            return got == _norm(expected)
        if qtype in ("matching", "match"):
            expected = (
                meta.get("answer")
                or meta.get("pairs")
                or (q_orig or {}).get("answer")
                or (q_orig or {}).get("pairs")
                or (q_orig or {}).get("correctPairs")
            )
            if expected is None:
                return False
            raw = sel_info.get("raw")
            if isinstance(expected, dict) and isinstance(raw, dict):
                try:
                    for k, v in expected.items():
                        if int(raw.get(str(k), raw.get(k))) != int(v):
                            return False
                    return True
                except (TypeError, ValueError):
                    return False
            return raw == expected
        if callable(_orig_grade):
            return _orig_grade(qtype, q_orig, sel_info, meta)
        return False

    par._grade_item = _grade_item

    if callable(_orig_build):
        def build_review(attempt_id: str):
            data = _orig_build(attempt_id)
            if not isinstance(data, dict):
                return data
            items = data.get("items") or []
            fixed = []
            for it in items:
                it = dict(it)
                qtype = str(it.get("type") or "").lower()
                if qtype in ("matching", "match"):
                    left = it.get("left") or []
                    right = it.get("right") or []
                    pairs = it.get("pairs")
                    if isinstance(pairs, dict) and left and right:
                        lines = []
                        for k, v in pairs.items():
                            try:
                                li, ri = int(k), int(v)
                                L = left[li] if 0 <= li < len(left) else str(li + 1)
                                R = right[ri] if 0 <= ri < len(right) else str(ri + 1)
                                lines.append(f"{L} → {R}")
                            except (TypeError, ValueError):
                                lines.append(f"{k} → {v}")
                        if lines:
                            it["correctAnswer"] = "\n".join(lines)
                    raw = it.get("studentRaw")
                    if isinstance(raw, dict) and left and right:
                        slines = []
                        for k, v in raw.items():
                            try:
                                li, ri = int(k), int(v)
                                L = left[li] if 0 <= li < len(left) else str(li + 1)
                                R = right[ri] if 0 <= ri < len(right) else str(ri + 1)
                                slines.append(f"{L} → {R}")
                            except (TypeError, ValueError):
                                slines.append(f"{k} → {v}")
                        if slines:
                            it["studentAnswer"] = "\n".join(slines)
                if qtype in ("short", "text", "number", "numeric", "open"):
                    expected = it.get("correctAnswer") or it.get("correctText")
                    got = it.get("studentAnswer")
                    if expected and got and not it.get("isBlank"):
                        g = _norm(str(got).lstrip("#"))
                        if qtype == "text" or "|" in str(expected):
                            keys = [x.strip() for x in str(expected).split("|") if x.strip()]
                            ok = any(_norm(k) == g or _norm(k) in g for k in keys)
                        else:
                            ok = g == _norm(expected)
                        it["isCorrect"] = ok
                        it["points"] = 1 if ok else 0
                        it["resultLabel"] = "Дуруст" if ok else "Нодуруст"
                fixed.append(it)
            data["items"] = fixed
            c = sum(1 for x in fixed if x.get("isCorrect"))
            w = sum(1 for x in fixed if not x.get("isCorrect") and not x.get("isBlank"))
            b = sum(1 for x in fixed if x.get("isBlank"))
            data["correct"] = c
            if data.get("stats"):
                data["stats"] = dict(data["stats"])
                data["stats"]["correct"] = c
                data["stats"]["wrong"] = w
                data["stats"]["blank"] = b
            return data

        par.build_review = build_review

    print("[boot] patch_review_text_fix: keyword text + readable matching")
    log.info("patch_review_text_fix installed")
