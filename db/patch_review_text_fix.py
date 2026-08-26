"""Boot patch: Review text keyword | matching + human-readable pairs.

Wraps the admin review view so fixes apply even when build_review is closed
over inside the materialized patch_attempt_review module.
"""
from __future__ import annotations
import logging

log = logging.getLogger("geografia.patch_review_text_fix")


def _norm(v):
    return " ".join(str(v or "").strip().split()).lower()


def _fmt_pairs(pairs, left, right):
    if not isinstance(pairs, dict) or not left or not right:
        return None
    lines = []
    for k, v in pairs.items():
        try:
            li, ri = int(k), int(v)
            L = left[li] if 0 <= li < len(left) else str(li + 1)
            R = right[ri] if 0 <= ri < len(right) else str(ri + 1)
            lines.append(f"{L} → {R}")
        except (TypeError, ValueError):
            lines.append(f"{k} → {v}")
    return "\n".join(lines) if lines else None


def _fix_items(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    items = data.get("items") or []
    fixed = []
    for it in items:
        if not isinstance(it, dict):
            fixed.append(it)
            continue
        it = dict(it)
        qtype = str(it.get("type") or "").lower()
        left = it.get("left") or it.get("leftItems") or []
        right = it.get("right") or it.get("rightItems") or []
        pairs = it.get("pairs")

        if qtype in ("matching", "match"):
            pretty = _fmt_pairs(pairs, left, right)
            if pretty:
                it["correctAnswer"] = pretty
            raw = it.get("studentRaw")
            if isinstance(raw, dict):
                sp = _fmt_pairs(raw, left, right)
                if sp:
                    it["studentAnswer"] = sp
            elif isinstance(it.get("studentAnswer"), str) and str(it.get("studentAnswer") or "").startswith("{"):
                try:
                    import ast
                    raw2 = ast.literal_eval(it["studentAnswer"])
                    if isinstance(raw2, dict):
                        sp = _fmt_pairs(raw2, left, right)
                        if sp:
                            it["studentAnswer"] = sp
                except Exception:
                    pass
            ca = it.get("correctAnswer")
            if ca is None or ca == "null" or isinstance(ca, dict):
                if pretty:
                    it["correctAnswer"] = pretty

        if qtype in ("short", "text", "number", "numeric", "open"):
            expected = it.get("correctAnswer") or it.get("correctText")
            got = it.get("studentAnswer")
            if expected is not None and got is not None and not it.get("isBlank"):
                g = _norm(str(got).lstrip("#"))
                if g and g != "—":
                    if qtype == "text" or "|" in str(expected):
                        keys = [x.strip() for x in str(expected).split("|") if x.strip()]
                        ok = any(_norm(k) == g or _norm(k) in g or g in _norm(k) for k in keys)
                    else:
                        ok = g == _norm(expected)
                    it["isCorrect"] = ok
                    it["isBlank"] = False
                    it["points"] = 1 if ok else 0
                    it["resultLabel"] = "Дуруст" if ok else "Нодуруст"

        fixed.append(it)

    data = dict(data)
    data["items"] = fixed
    c = sum(1 for x in fixed if isinstance(x, dict) and x.get("isCorrect"))
    w = sum(
        1
        for x in fixed
        if isinstance(x, dict) and not x.get("isCorrect") and not x.get("isBlank")
    )
    b = sum(1 for x in fixed if isinstance(x, dict) and x.get("isBlank"))
    data["correct"] = c
    if isinstance(data.get("stats"), dict):
        st = dict(data["stats"])
        st["correct"] = c
        st["wrong"] = w
        st["blank"] = b
        data["stats"] = st
    return data


def install(app=None):
    try:
        import db.patch_attempt_review as par
    except Exception:
        try:
            import patch_attempt_review as par  # type: ignore
        except Exception as e:
            par = None
            log.warning("patch_attempt_review import: %s", e)

    if par is not None:
        _orig_build = getattr(par, "build_review", None)
        if callable(_orig_build):
            def build_review(attempt_id: str, _orig=_orig_build):
                return _fix_items(_orig(attempt_id))
            par.build_review = build_review

    if app is None:
        print("[boot] patch_review_text_fix: no app (module only)")
        return

    endpoint = "admin_attempt_review"
    if endpoint not in getattr(app, "view_functions", {}):
        print("[boot] patch_review_text_fix: endpoint not yet registered")
        return

    from flask import jsonify

    orig_view = app.view_functions[endpoint]

    def _wrapped(attempt_id: str, *args, **kwargs):
        resp = orig_view(attempt_id, *args, **kwargs)
        try:
            if hasattr(resp, "get_json"):
                data = resp.get_json(silent=True)
                if isinstance(data, dict) and data.get("items"):
                    return jsonify(_fix_items(data))
        except Exception as e:
            log.warning("review wrap: %s", e)
        return resp

    app.view_functions[endpoint] = _wrapped
    print("[boot] patch_review_text_fix: wrapped admin_attempt_review + keyword/matching")
    log.info("patch_review_text_fix installed")
