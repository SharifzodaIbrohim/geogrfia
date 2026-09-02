"""Fix Admin Review display only: isCorrect for shuffled MCQ + single-source stats.

Does not change student scoring/submit.
Install AFTER patch_attempt_review.
"""
from __future__ import annotations
import logging
log = logging.getLogger("geografia.patch_review_display_fix")

def install(app=None) -> None:
    try:
        import db.patch_attempt_review as par
    except Exception:
        try:
            import patch_attempt_review as par
        except Exception as e:
            log.warning("no patch_attempt_review: %s", e)
            par = None

    if par is not None and hasattr(par, "_grade_item"):
        _orig_grade = par._grade_item
        def _grade_item_fixed(qtype, q_orig, sel_info, meta=None):
            meta = meta or {}
            qtype = (qtype or "single").lower()
            if qtype in ("short", "text", "number", "numeric", "open", "essay", "written", "matching", "match"):
                return _orig_grade(qtype, q_orig, sel_info, meta)
            try:
                from db.patch_attempt_review import _norm_text, _correct_text, _correct_index
            except Exception:
                from patch_attempt_review import _norm_text, _correct_text, _correct_index
            if sel_info.get("text") is None and sel_info.get("index") is None and sel_info.get("raw") is None:
                return False
            ct = meta.get("correctText") or _correct_text(q_orig)
            st = sel_info.get("text")
            if st is not None and ct is not None and _norm_text(st) == _norm_text(ct):
                return True
            ci = meta.get("correctIndex")
            if ci is None:
                ci = _correct_index(q_orig)
            om = meta.get("optionMap")
            if sel_info.get("index") is not None and ci is not None and om:
                try:
                    i = int(sel_info["index"])
                    if 0 <= i < len(om) and int(om[i]) == int(ci):
                        return True
                except (TypeError, ValueError):
                    pass
                return False
            if sel_info.get("index") is not None and ci is not None:
                try:
                    return int(sel_info["index"]) == int(ci)
                except (TypeError, ValueError):
                    return False
            return False
        par._grade_item = _grade_item_fixed
        print("[boot] patch_review_display_fix: MCQ isCorrect via optionMap only")

    if par is not None and hasattr(par, "build_review"):
        _orig_build = par.build_review
        def build_review_fixed(attempt_id: str) -> dict:
            data = _orig_build(attempt_id)
            items = data.get("items") or []
            correct = wrong = blank = 0
            earned = 0.0
            total_max = 0.0
            for it in items:
                max_s = float(it.get("maxScore") or 1)
                pts = float(it.get("points") or 0)
                total_max += max_s
                earned += pts
                if it.get("isBlank"):
                    blank += 1
                    it["resultLabel"] = "Беҷавоб"
                elif it.get("isCorrect"):
                    correct += 1
                    it["resultLabel"] = "Дуруст"
                else:
                    wrong += 1
                    rl = str(it.get("resultLabel") or "")
                    if not rl.startswith("Қисман"):
                        it["resultLabel"] = "Нодуруст"
            total = len(items) or int(data.get("total") or 0)
            if total_max > 0:
                score = int(round((earned / total_max) * 100))
            elif total:
                score = int(round((correct / total) * 100))
            else:
                score = int(data.get("score") or 0)
            try:
                pass_score = int(data.get("passScore") if data.get("passScore") is not None else 70)
            except (TypeError, ValueError):
                pass_score = 70
            stored = str(data.get("status") or "").lower()
            if stored in ("timeout", "in_progress", "started"):
                status = data.get("status")
            else:
                status = "passed" if score >= pass_score else "failed"
            data["earned"] = round(earned, 2)
            data["totalMax"] = round(total_max, 2)
            data["score"] = score
            data["scorePercent"] = score
            data["correct"] = correct
            data["correctCount"] = correct
            data["wrongCount"] = wrong
            data["blankCount"] = blank
            data["total"] = total
            data["passScore"] = pass_score
            data["status"] = status
            data["stats"] = {"correct": correct, "wrong": wrong, "blank": blank, "total": total}
            return data
        par.build_review = build_review_fixed
        print("[boot] patch_review_display_fix: review stats single source of truth")

    try:
        from db import repo
        _orig_list = repo.list_results
        def list_results_fixed(olympiad_id=None):
            rows = _orig_list(olympiad_id)
            out = []
            for r in rows or []:
                r = dict(r)
                if r.get("earned") is None and r.get("correct") is not None:
                    r["earned"] = r["correct"]
                if r.get("totalMax") is None and r.get("total") is not None:
                    r["totalMax"] = r["total"]
                if r.get("scorePercent") is None and r.get("score") is not None:
                    r["scorePercent"] = r["score"]
                if r.get("correctCount") is None and r.get("correct") is not None:
                    r["correctCount"] = r["correct"]
                out.append(r)
            return out
        repo.list_results = list_results_fixed
        print("[boot] patch_review_display_fix: list_results earned/totalMax")
    except Exception as e:
        log.warning("list_results wrap: %s", e)
    print("[boot] patch_review_display_fix installed")
