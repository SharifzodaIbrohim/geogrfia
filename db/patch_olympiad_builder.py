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

    try:
        from flask import request, jsonify

        target_ep = None
        orig = None
        for rule in list(app.url_map.iter_rules()):
            if str(rule.rule) == "/api/admin/olympiads" and "POST" in (rule.methods or set()):
                target_ep = rule.endpoint
                orig = app.view_functions.get(target_ep)
                break
        if orig is None and "admin_create_olympiad" in app.view_functions:
            target_ep = "admin_create_olympiad"
            orig = app.view_functions[target_ep]

        if orig is not None:

            def admin_create_olympiad_multi(*args, **kwargs):
                payload = request.get_json(silent=True) or {}
                title = str(payload.get("title") or "").strip()
                raw_questions = payload.get("questions") or []
                if not title:
                    return jsonify({"error": "Унвонро ворид кунед."}), 400
                if not isinstance(raw_questions, list) or len(raw_questions) < 1:
                    return jsonify({"error": "Камаш 1 савол лозим аст."}), 400

                questions = []
                for i, q in enumerate(raw_questions):
                    if not isinstance(q, dict):
                        return jsonify({"error": f"Саволи {i + 1} нодуруст аст."}), 400
                    nq = normalize_question(i, q)
                    qtype = str(nq.get("type") or "single")
                    text = str(nq.get("text") or "").strip()
                    if not text:
                        return jsonify({"error": f"Саволи {i + 1}: матн холӣ."}), 400
                    if qtype == "single":
                        opts = [str(o).strip() for o in (nq.get("options") or []) if str(o).strip()]
                        if len(opts) < 2:
                            return jsonify({"error": f"Саволи {i + 1}: ҳадди ақал 2 вариант."}), 400
                        ans = nq.get("answer")
                        try:
                            ans = int(ans)
                        except (TypeError, ValueError):
                            ans = 0
                        if ans < 0 or ans >= len(opts):
                            return jsonify({"error": f"Ҷавоби дурусти саволи {i + 1} нодуруст аст."}), 400
                        nq["options"] = opts
                        nq["answer"] = ans
                    elif qtype == "short":
                        if not str(nq.get("correctText") or "").strip():
                            return jsonify({"error": f"Саволи {i + 1}: ҷавоби дуруст лозим."}), 400
                    elif qtype == "matching":
                        left = nq.get("leftItems") or []
                        right = nq.get("rightItems") or []
                        pairs = nq.get("pairs") or {}
                        if len(left) < 2:
                            return jsonify({"error": f"Саволи {i + 1}: мувофиқат — ҳадди ақал 2 банди чап."}), 400
                        if len(right) < 1:
                            return jsonify({"error": f"Саволи {i + 1}: мувофиқат — бандҳои рост лозим."}), 400
                        if not pairs:
                            pairs = {str(j): j for j in range(len(left))}
                            nq["pairs"] = pairs
                    questions.append(nq)

                payload = dict(payload)
                payload["questions"] = questions
                payload["title"] = title
                if "isActive" not in payload and "active" in payload:
                    payload["isActive"] = bool(payload.get("active"))
                if "startTime" not in payload and payload.get("startAt"):
                    payload["startTime"] = payload.get("startAt")
                if "endTime" not in payload and payload.get("endAt"):
                    payload["endTime"] = payload.get("endAt")

                try:
                    import db.repo as repo
                except Exception:
                    try:
                        import repo  # type: ignore
                    except Exception:
                        repo = None

                has_multi = any(str(q.get("type")) != "single" for q in questions)
                if has_multi and repo is not None and getattr(repo, "create_olympiad", None):
                    try:
                        admin = None
                        try:
                            admin_fn = None
                            globs = getattr(orig, "__globals__", {}) or {}
                            for name in ("require_admin", "_require_admin", "require_admin_user"):
                                if name in globs and callable(globs[name]):
                                    admin_fn = globs[name]
                                    break
                            if callable(admin_fn):
                                admin = admin_fn()
                        except Exception as e:
                            log.warning("require_admin: %s", e)
                            admin = None
                        if isinstance(admin, tuple):
                            return admin
                        otype = str(payload.get("type") or "olympiad")
                        if otype not in ("olympiad", "quiz"):
                            otype = "olympiad"
                        try:
                            pass_score = int(payload.get("passScore", 70))
                        except (TypeError, ValueError):
                            pass_score = 70
                        data = {
                            "title": title,
                            "type": otype,
                            "passScore": pass_score,
                            "isActive": bool(payload.get("isActive", payload.get("active", False))),
                            "startTime": payload.get("startTime") or payload.get("startAt"),
                            "endTime": payload.get("endTime") or payload.get("endAt"),
                            "questions": questions,
                            "showResultsToStudents": bool(payload.get("showResultsToStudents", True)),
                            "durationSec": payload.get("durationSec"),
                            "createdBy": (admin or {}).get("login") if isinstance(admin, dict) else None,
                        }
                        olympiad = repo.create_olympiad(data)
                        if isinstance(olympiad, dict):
                            oid = olympiad.get("id")
                            return jsonify({"olympiad": olympiad, "id": oid, "ok": True}), 201
                        return jsonify({"olympiad": olympiad, "ok": True}), 201
                    except Exception as e:
                        log.exception("multi-type create via repo")
                        return jsonify({"error": str(e)}), 500

                return orig(*args, **kwargs)

            admin_create_olympiad_multi.__name__ = getattr(orig, "__name__", "admin_create_olympiad")
            app.view_functions[target_ep] = admin_create_olympiad_multi
            print("[boot] patch_olympiad_builder: POST /api/admin/olympiads multi-type wrap")
        else:
            print("[boot] patch_olympiad_builder: create endpoint not found")
    except Exception as e:
        log.warning("create wrap failed: %s", e)
        print("[boot] patch_olympiad_builder: create wrap failed:", e)

    print("[boot] patch_olympiad_builder: multi-type + maxScore + matching partial")
