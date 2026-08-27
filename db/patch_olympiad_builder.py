"""Patch olympiad create/scoring for multi-type questions + showResultsToStudents."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("geografia.patch_olympiad_builder")

PENDING_MSG = (
    "Шумо бо муваффақият супоридед. Лутфан интизор шавед, то баллҳоятон муайян шаванд."
)


def _norm_text(s: Any) -> str:
    return " ".join(str(s or "").strip().lower().split())


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
        raise ValueError(f"Саволи {i + 1}: матн холӣ")
    try:
        max_score = float(q.get("maxScore", 1))
    except (TypeError, ValueError):
        max_score = 1.0
    if max_score <= 0:
        max_score = 1.0

    if qtype == "single":
        options = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
        if len(options) < 2:
            raise ValueError(f"Саволи {i + 1}: ҳадди ақал 2 вариант")
        try:
            answer = int(q.get("answer", 0))
        except (TypeError, ValueError):
            answer = 0
        ca = q.get("correctAnswer")
        if isinstance(ca, str) and len(ca.strip()) == 1 and ca.strip().isalpha():
            answer = ord(ca.strip().upper()) - ord("A")
        elif isinstance(ca, int):
            answer = ca
        if answer < 0 or answer >= len(options):
            raise ValueError(f"Саволи {i + 1}: ҷавоби дуруст нодуруст")
        return {"id": i + 1, "type": "single", "text": text, "options": options, "answer": answer, "maxScore": max_score}

    if qtype == "short":
        correct = str(
            q.get("correctText")
            or q.get("correctAnswer")
            or q.get("answerText")
            or (q.get("answer") if not isinstance(q.get("answer"), (list, dict)) else "")
            or ""
        ).strip()
        if not correct:
            raise ValueError(f"Саволи {i + 1}: ҷавоби дуруст лозим")
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
            raise ValueError(f"Саволи {i + 1}: ҷавоби дуруст лозим")
        try:
            ms = float(q.get("maxScore", len(left) or 1))
        except (TypeError, ValueError):
            ms = float(len(left) or 1)
        if ms <= 0:
            ms = float(len(left) or 1)
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

    correct = str(
        q.get("correctText") or q.get("correctAnswer") or q.get("answerText") or ""
    ).strip()
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
        _orig_resolve = getattr(eng, "_resolve_selection", None)

        def _resolve_selection(q, selected):
            qtype = str((q or {}).get("type") or "single")
            if qtype == "single" and callable(_orig_resolve):
                try:
                    return _orig_resolve(q, selected)
                except TypeError:
                    pass
            earned, _ = score_question(q or {}, selected)
            return selected, earned > 0

        def _public_questions(qs_src: list) -> list:
            import secrets

            order = list(range(len(qs_src or [])))
            secrets.SystemRandom().shuffle(order)
            out = []
            for orig_i in order:
                q = (qs_src or [])[orig_i] or {}
                qid = q.get("id")
                if qid is None:
                    qid = str(orig_i)
                qtype = str(q.get("type") or "single")
                sanitize = getattr(eng, "_sanitize_options", lambda x: list(x or []))
                item = {
                    "id": str(qid),
                    "type": qtype,
                    "text": q.get("text"),
                    "options": sanitize(q.get("options")),
                    "originalIndex": orig_i,
                }
                if qtype == "matching":
                    item["leftItems"] = list(q.get("leftItems") or [])
                    item["rightItems"] = list(q.get("rightItems") or [])
                if qtype in ("short", "text"):
                    item["inputType"] = "text"
                forbidden = getattr(eng, "_FORBIDDEN", getattr(eng, "_FORBIDDEN_Q_KEYS", set()))
                for bad in forbidden:
                    item.pop(bad, None)
                out.append(item)
            return out

        eng._resolve_selection = _resolve_selection
        eng._public_questions = _public_questions
        log.info("olympiad_engine multi-type resolve patched")

    if app is None:
        return

    from flask import request, jsonify

    try:
        import db.repo as repo
    except Exception:
        import repo  # type: ignore

    def admin_create_olympiad():
        globs = app.view_functions["admin_list_olympiads"].__globals__
        require_admin = globs.get("require_admin")
        normalize_time_field = globs.get("normalize_time_field")
        public_olympiad = globs.get("public_olympiad")
        parse_dt = globs.get("parse_dt")
        admin = require_admin() if require_admin else None
        if not admin:
            return jsonify({"error": "Дастрасӣ рад шуд."}), 401

        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        otype = str(payload.get("type", "olympiad")).strip() or "olympiad"
        if otype not in ("olympiad", "quiz"):
            otype = "olympiad"
        try:
            pass_score = int(payload.get("passScore", 70))
        except (TypeError, ValueError):
            pass_score = 70
        pass_score = max(0, min(100, pass_score))

        start_time = normalize_time_field(payload.get("startTime")) if normalize_time_field else payload.get("startTime")
        end_time = normalize_time_field(payload.get("endTime")) if normalize_time_field else payload.get("endTime")
        if start_time and end_time and parse_dt:
            s, e = parse_dt(start_time), parse_dt(end_time)
            if s and e and e <= s:
                return jsonify({"error": "Вақти анҷом бояд баъд аз оғоз бошад."}), 400

        raw_questions = payload.get("questions") or []
        if not title:
            return jsonify({"error": "Унвонро ворид кунед."}), 400
        if not isinstance(raw_questions, list) or len(raw_questions) < 1:
            return jsonify({"error": "Камаш 1 савол лозим аст."}), 400

        questions = []
        try:
            for i, q in enumerate(raw_questions):
                if not isinstance(q, dict):
                    raise ValueError(f"Саволи {i + 1} нодуруст")
                questions.append(normalize_question(i, q))
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

        show_results = payload.get("showResultsToStudents")
        if show_results is None:
            show_results = False

        olympiad = repo.create_olympiad(
            {
                "title": title,
                "type": otype,
                "passScore": pass_score,
                "isActive": bool(payload.get("isActive", False)),
                "startTime": start_time,
                "endTime": end_time,
                "questions": questions,
                "showResultsToStudents": bool(show_results),
                "createdBy": admin.get("login") if isinstance(admin, dict) else str(admin),
            }
        )
        po = public_olympiad(olympiad, include_answers=True) if public_olympiad else olympiad
        if isinstance(po, dict):
            po["showResultsToStudents"] = bool(olympiad.get("showResultsToStudents", False))
        return jsonify({"olympiad": po})

    app.view_functions["admin_create_olympiad"] = admin_create_olympiad

    if "admin_patch_olympiad" in app.view_functions:
        _orig_patch = app.view_functions["admin_patch_olympiad"]

        def admin_patch_wrap(olympiad_id: str):
            payload = request.get_json(silent=True) or {}
            if "showResultsToStudents" not in payload:
                return _orig_patch(olympiad_id)
            globs = app.view_functions["admin_list_olympiads"].__globals__
            require_admin = globs.get("require_admin")
            public_olympiad = globs.get("public_olympiad")
            admin = require_admin() if require_admin else None
            if not admin:
                return jsonify({"error": "Дастрасӣ рад шуд."}), 401
            patch = {"showResultsToStudents": bool(payload["showResultsToStudents"])}
            if "isActive" in payload:
                patch["isActive"] = bool(payload["isActive"])
            o = None
            if hasattr(repo, "update_olympiad"):
                o = repo.update_olympiad(olympiad_id, patch)
            elif hasattr(repo, "patch_olympiad"):
                o = repo.patch_olympiad(olympiad_id, patch)
            if o is None:
                return jsonify({"error": "Навсозӣ нашуд"}), 400
            po = public_olympiad(o, include_answers=True) if public_olympiad else o
            if isinstance(po, dict):
                po["showResultsToStudents"] = bool(o.get("showResultsToStudents", False))
            return jsonify({"olympiad": po})

        app.view_functions["admin_patch_olympiad"] = admin_patch_wrap

    try:
        globs = app.view_functions["admin_list_olympiads"].__globals__
        _po = globs.get("public_olympiad")

        def public_olympiad(o, include_answers=False):
            base = _po(o, include_answers=include_answers) if _po else dict(o)
            if isinstance(base, dict):
                base["showResultsToStudents"] = bool(o.get("showResultsToStudents", False))
                if include_answers and base.get("questions"):
                    src = {str(q.get("id")): q for q in (o.get("questions") or [])}
                    rich = []
                    for q in base["questions"]:
                        full = dict(q)
                        src_q = src.get(str(q.get("id")), {})
                        for k in ("type", "correctText", "leftItems", "rightItems", "pairs", "pairsText", "maxScore", "manual", "answer"):
                            if k in src_q:
                                full[k] = src_q[k]
                        rich.append(full)
                    base["questions"] = rich
            return base

        globs["public_olympiad"] = public_olympiad
    except Exception as e:
        log.warning("public_olympiad wrap: %s", e)

    print("[boot] patch_olympiad_builder: multi-type + maxScore + showResultsToStudents")
