"""P1 Admin attempt review — prefer plain src, else _par_b64_*.txt.
Includes display-only fixes for Admin Results (isCorrect + stats).
"""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

_dir = Path(__file__).resolve().parent
_plain = _dir / "patch_attempt_review_src.py"
if not _plain.is_file():
    _plain = _dir.parent / "patch_attempt_review.py"

if _plain.is_file() and _plain.stat().st_size > 2000:
    _src = _plain.read_text(encoding="utf-8")
else:
    _parts = sorted(_dir.glob("_par_b64_*.txt"))
    if not _parts:
        _parts = sorted(_dir.parent.glob("_par_b64_*.txt"))
    if not _parts:
        raise RuntimeError("patch_attempt_review: missing src and _par_b64_*.txt")
    _b64 = "".join(p.read_text(encoding="utf-8").strip() for p in _parts)
    _b64 += "=" * ((4 - len(_b64) % 4) % 4)
    _src = zlib.decompress(base64.b64decode(_b64)).decode("utf-8")

_g: dict = {"__name__": "patch_attempt_review"}
exec(compile(_src, "patch_attempt_review_full.py", "exec"), _g)

# ---- display fixes (Admin Results only; does not change student scoring) ----
_orig_grade = _g.get("_grade_item")
_orig_build = _g.get("build_review")

if callable(_orig_grade):
    def _grade_item_fixed(qtype, q_orig, sel_info, meta=None):
        meta = meta or {}
        qtype = (qtype or "single").lower()
        if qtype in ("short", "text", "number", "numeric", "open", "essay", "written", "matching", "match"):
            return _orig_grade(qtype, q_orig, sel_info, meta)
        _norm_text = _g.get("_norm_text")
        _correct_text = _g.get("_correct_text")
        _correct_index = _g.get("_correct_index")
        if sel_info.get("text") is None and sel_info.get("index") is None and sel_info.get("raw") is None:
            return False
        ct = meta.get("correctText") or (_correct_text(q_orig) if callable(_correct_text) else None)
        st = sel_info.get("text")
        if st is not None and ct is not None and callable(_norm_text) and _norm_text(st) == _norm_text(ct):
            return True
        ci = meta.get("correctIndex")
        if ci is None and callable(_correct_index):
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
    _g["_grade_item"] = _grade_item_fixed

if callable(_orig_build):
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
    _g["build_review"] = build_review_fixed

install = _g["install"]
build_review = _g.get("build_review")
for _k, _v in list(_g.items()):
    if _k in ("install", "build_review") or (not _k.startswith("_") and callable(_v)):
        globals()[_k] = _v

print("[boot] patch_attempt_review: loaded + display fixes (isCorrect/stats)")
