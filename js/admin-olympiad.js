/* Admin olympiad builder — multi-type questions + local copy + results visibility */
(function () {
  var TOKEN_KEY = "geo_admin_token";
  var qSeq = 0;
  var lock = false;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&" + "amp;")
      .replace(/</g, "&" + "lt;")
      .replace(/>/g, "&" + "gt;")
      .replace(/"/g, "&" + "quot;")
      .replace(/'/g, "&#39;");
  }

  function getToken() {
    return (
      localStorage.getItem(TOKEN_KEY) ||
      sessionStorage.getItem(TOKEN_KEY) ||
      localStorage.getItem("adminToken") ||
      ""
    );
  }

  async function api(path, options) {
    options = options || {};
    var headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    var token = getToken();
    if (token) headers["X-Admin-Token"] = token;
    var res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: "include" }));
    var data = await res.json().catch(function () {
      return {};
    });
    if (!res.ok) throw new Error(data.error || data.message || "Хато");
    return data;
  }

  function forceDownload(filename, text, mime) {
    try {
      var blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        try {
          URL.revokeObjectURL(url);
          a.remove();
        } catch (e) {}
      }, 1500);
    } catch (e) {
      console.warn(e);
    }
  }

  function safeName(s) {
    return String(s || "file")
      .replace(/[^\w\u0400-\u04FF\-]+/g, "_")
      .slice(0, 60);
  }

  function listEl() {
    return document.getElementById("questionsList");
  }

  function typeLabel(t) {
    return (
      {
        single: "Интихоб (A–D)",
        short: "Ҷавоби кӯтоҳ / рақамӣ",
        matching: "Мувофиқат",
        text: "Шарҳ / мафҳум (матн)",
      }[t] || t
    );
  }

  function optRow(name, checked, val) {
    return (
      '<div class="opt-row" style="display:flex;gap:.4rem;align-items:center;margin:.25rem 0">' +
      '<input type="radio" name="' +
      name +
      '" ' +
      (checked ? "checked" : "") +
      " />" +
      '<input type="text" class="opt-text" placeholder="Вариант" value="' +
      esc(val || "") +
      '" style="flex:1" />' +
      '<button type="button" class="btn small danger opt-del">×</button></div>'
    );
  }

  function singleBody(pre) {
    var name = "corr-" + qSeq;
    var opts = (pre && pre.options) || ["", "", "", ""];
    var html =
      '<input class="q-text" placeholder="Матни савол" style="width:100%;margin:.35rem 0" value="' +
      esc((pre && pre.text) || "") +
      '" />' +
      '<div class="q-options"></div>' +
      '<button type="button" class="btn small add-opt">+ Вариант</button>';
    var wrap = document.createElement("div");
    wrap.innerHTML = html;
    var box = wrap.querySelector(".q-options");
    var ans = pre && typeof pre.answer === "number" ? pre.answer : 0;
    opts.forEach(function (o, i) {
      box.insertAdjacentHTML("beforeend", optRow(name, i === ans, o));
    });
    return wrap.innerHTML;
  }

  function shortBody(pre) {
    return (
      '<textarea class="q-text" rows="2" placeholder="Матни савол" style="width:100%;margin:.35rem 0">' +
      esc((pre && pre.text) || "") +
      "</textarea>" +
      '<label>Ҷавоби дуруст <input class="q-correct" style="width:100%" value="' +
      esc((pre && pre.correctText) || "") +
      '" placeholder="масалан: 42 ё Душанбе" /></label>'
    );
  }

  function matchBody(pre) {
    return (
      '<textarea class="q-text" rows="2" placeholder="Мувофиқатро муайян намоед" style="width:100%;margin:.35rem 0">' +
      esc((pre && pre.text) || "Мувофиқатро муайян намоед") +
      "</textarea>" +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem">' +
      '<div><strong>Чап</strong><textarea class="q-left" rows="5" style="width:100%" placeholder="ҳар банд дар сатри нав">' +
      esc(((pre && pre.leftItems) || []).join("\n")) +
      "</textarea></div>" +
      '<div><strong>Рост</strong><textarea class="q-right" rows="5" style="width:100%" placeholder="ҳар банд дар сатри нав">' +
      esc(((pre && pre.rightItems) || []).join("\n")) +
      "</textarea></div></div>" +
      '<label style="display:block;margin-top:.35rem">Ҷуфтҳо (1-2, 2-1…) <input class="q-pairs" style="width:100%" value="' +
      esc((pre && pre.pairsText) || "") +
      '" /></label>'
    );
  }

  function textBody(pre) {
    return (
      '<textarea class="q-text" rows="2" placeholder="Мафҳум" style="width:100%;margin:.35rem 0">' +
      esc((pre && pre.text) || "") +
      "</textarea>" +
      '<label>Калимаҳои калидӣ (ихтиёрӣ, | ҷудо) <input class="q-correct" style="width:100%" value="' +
      esc((pre && pre.correctText) || "") +
      '" /></label>'
    );
  }

  function scoreField(prefill, type) {
    var def = 1;
    if (prefill && prefill.maxScore != null && !isNaN(Number(prefill.maxScore))) {
      def = Number(prefill.maxScore);
    } else if (type === "matching" && prefill && (prefill.leftItems || []).length) {
      def = (prefill.leftItems || []).length || 1;
    }
    if (def < 0.5) def = 1;
    return (
      '<label style="display:flex;align-items:center;gap:.4rem;margin:.4rem 0;flex-wrap:wrap">' +
      '<span style="font-weight:600">Хол / балл</span>' +
      '<input type="number" class="q-maxscore" min="0.5" step="0.5" value="' +
      esc(String(def)) +
      '" style="width:5rem" />' +
      '<span class="q-score-label muted" style="font-size:.9rem">Хол: ' +
      esc(String(def)) +
      "</span></label>"
    );
  }

  function updateTotalScore() {
    var el = document.getElementById("olyTotalScore");
    if (!el) {
      var list = listEl();
      if (!list || !list.parentElement) return;
      el = document.createElement("div");
      el.id = "olyTotalScore";
      el.style.cssText = "font-weight:700;margin:.5rem 0;padding:.4rem .6rem;background:#f0f7ff;border-radius:6px";
      list.parentElement.insertBefore(el, list);
    }
    var sum = 0;
    var cards = listEl() ? listEl().querySelectorAll(".question-card") : [];
    cards.forEach(function (card) {
      var inp = card.querySelector(".q-maxscore");
      var n = inp ? Number(inp.value) : 1;
      if (isNaN(n) || n < 0) n = 0;
      sum += n;
      var lab = card.querySelector(".q-score-label");
      if (lab) lab.textContent = "Хол: " + (isNaN(n) ? "—" : n);
    });
    el.textContent = "Ҷамъи холҳо: " + (Math.round(sum * 100) / 100);
  }

  function bindScoreInput(card) {
    var inp = card.querySelector(".q-maxscore");
    if (!inp) return;
    inp.addEventListener("input", updateTotalScore);
    inp.addEventListener("change", updateTotalScore);
  }

  function addQuestion(type, prefill) {
    var list = listEl();
    if (!list) return;
    type = type || "single";
    qSeq += 1;
    var card = document.createElement("div");
    card.className = "question-card card";
    card.dataset.type = type;
    card.style.marginBottom = ".75rem";
    card.style.padding = ".75rem";
    var head =
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem">' +
      "<strong>Савол · " +
      esc(typeLabel(type)) +
      "</strong>" +
      '<button type="button" class="btn small danger q-remove">×</button></div>';
    var body =
      type === "short"
        ? shortBody(prefill)
        : type === "matching"
          ? matchBody(prefill)
          : type === "text"
            ? textBody(prefill)
            : singleBody(prefill);
    card.innerHTML = head + scoreField(prefill, type) + body;
    list.appendChild(card);
    card.querySelector(".q-remove").onclick = function () {
      card.remove();
      updateTotalScore();
    };
    bindScoreInput(card);
    updateTotalScore();
    var addOpt = card.querySelector(".add-opt");
    if (addOpt) {
      var name = "corr-" + qSeq;
      addOpt.onclick = function () {
        card.querySelector(".q-options").insertAdjacentHTML("beforeend", optRow(name, false, ""));
        bindOptDel(card);
      };
      bindOptDel(card);
    }
  }

  function bindOptDel(card) {
    card.querySelectorAll(".opt-del").forEach(function (b) {
      b.onclick = function () {
        b.parentElement.remove();
      };
    });
  }

  function parsePairs(text, leftLen) {
    var map = {};
    String(text || "")
      .split(/[,;\s]+/)
      .forEach(function (p) {
        var m = p.match(/(\d+)\D+(\d+)/);
        if (!m) return;
        var a = parseInt(m[1], 10) - 1;
        var b = parseInt(m[2], 10) - 1;
        if (a >= 0 && a < leftLen && b >= 0) map[String(a)] = b;
      });
    return map;
  }

  function readMaxScore(card, fallback) {
    var inp = card.querySelector(".q-maxscore");
    var n = inp ? Number(inp.value) : NaN;
    if (isNaN(n) || n < 0) n = fallback != null ? fallback : 1;
    if (n < 0.5) n = 0.5;
    return Math.round(n * 100) / 100;
  }

  function collectQuestions() {
    var cards = listEl() ? listEl().querySelectorAll(".question-card") : [];
    var out = [];
    cards.forEach(function (card, i) {
      var type = card.dataset.type || "single";
      var textEl = card.querySelector(".q-text");
      var text = textEl ? String(textEl.value || "").trim() : "";
      if (type === "single") {
        var opts = [];
        var ans = 0;
        card.querySelectorAll(".opt-row").forEach(function (row) {
          var t = row.querySelector(".opt-text");
          var v = t ? String(t.value || "").trim() : "";
          if (v) {
            if (row.querySelector('input[type="radio"]').checked) ans = opts.length;
            opts.push(v);
          }
        });
        out.push({ id: i + 1, type: "single", text: text, options: opts, answer: ans, maxScore: readMaxScore(card, 1) });
      } else if (type === "short") {
        var c = card.querySelector(".q-correct");
        var ct = c ? String(c.value || "").trim() : "";
        out.push({
          id: i + 1,
          type: "short",
          text: text,
          correctText: ct,
          correctAnswer: ct,
          maxScore: readMaxScore(card, 1),
        });
      } else if (type === "matching") {
        var left = String(card.querySelector(".q-left").value || "")
          .split("\n")
          .map(function (s) {
            return s.trim();
          })
          .filter(Boolean);
        var right = String(card.querySelector(".q-right").value || "")
          .split("\n")
          .map(function (s) {
            return s.trim();
          })
          .filter(Boolean);
        var pairsText = card.querySelector(".q-pairs").value || "";
        var pairs = parsePairs(pairsText, left.length);
        out.push({
          id: i + 1,
          type: "matching",
          text: text,
          leftItems: left,
          rightItems: right,
          pairs: pairs,
          correctPairs: pairs,
          pairsText: pairsText,
          maxScore: readMaxScore(card, left.length || 1),
        });
      } else {
        var cc = card.querySelector(".q-correct");
        var cct = cc ? String(cc.value || "").trim() : "";
        out.push({
          id: i + 1,
          type: "text",
          text: text,
          correctText: cct,
          correctAnswer: cct,
          maxScore: readMaxScore(card, 1),
          manual: !cct,
        });
      }
    });
    return out;
  }

  function buildLocalHtml(payload, saved) {
    var qs = payload.questions || [];
    var rows = qs
      .map(function (q, i) {
        var body = esc(q.text);
        if (q.type === "single") {
          body +=
            "<ol>" +
            (q.options || [])
              .map(function (o, j) {
                return "<li>" + esc(o) + (j === q.answer ? " ✓" : "") + "</li>";
              })
              .join("") +
            "</ol>";
        } else if (q.type === "short" || q.type === "text") {
          body += "<p><b>Ҷавоб:</b> " + esc(q.correctText || "—") + "</p>";
        } else if (q.type === "matching") {
          body +=
            "<p>Чап: " +
            esc((q.leftItems || []).join("; ")) +
            " | Рост: " +
            esc((q.rightItems || []).join("; ")) +
            " | Ҷуфт: " +
            esc(q.pairsText || "") +
            "</p>";
        }
        return "<h3>" + (i + 1) + ". [" + esc(q.type) + "]</h3><div>" + body + "</div>";
      })
      .join("");
    return (
      "<!DOCTYPE html><html><head><meta charset=UTF-8><title>" +
      esc(payload.title) +
      "</title></head><body><h1>" +
      esc(payload.title) +
      "</h1><p>ID: " +
      esc((saved && saved.id) || "") +
      "</p>" +
      rows +
      "</body></html>"
    );
  }

  function buildLocalTxt(payload, saved) {
    var lines = [payload.title, "ID: " + ((saved && saved.id) || ""), ""];
    (payload.questions || []).forEach(function (q, i) {
      lines.push(i + 1 + ". [" + q.type + "] " + q.text);
      if (q.type === "single")
        (q.options || []).forEach(function (o, j) {
          lines.push("  " + (j === q.answer ? ">" : "-") + " " + o);
        });
      if (q.correctText) lines.push("  Ҷавоб: " + q.correctText);
      if (q.leftItems) lines.push("  Чап: " + q.leftItems.join(" | "));
      if (q.rightItems) lines.push("  Рост: " + q.rightItems.join(" | "));
      lines.push("");
    });
    return lines.join("\n");
  }

  async function saveLocalCopy(payload, saved) {
    var base = safeName(payload.title || "olympiad") + "_" + safeName((saved && saved.id) || "new");
    forceDownload(base + ".html", buildLocalHtml(payload, saved), "text/html;charset=utf-8");
    forceDownload(base + ".txt", buildLocalTxt(payload, saved), "text/plain;charset=utf-8");
  }

  async function onSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (lock) return false;
    lock = true;
    var msg = document.getElementById("olyFormMsg") || document.getElementById("olyMsg");
    try {
      var title = String((document.getElementById("olyTitle") || {}).value || "").trim();
      if (!title) throw new Error("Унвонро ворид кунед");
      var questions = collectQuestions();
      if (!questions.length) throw new Error("Ҳадди ақал 1 савол — тугмаҳои + Интихоб / + Ҷавоби кӯтоҳ / …");
      for (var i = 0; i < questions.length; i++) {
        var q = questions[i];
        if (!q.text) throw new Error("Саволи " + (i + 1) + ": матн холӣ");
        if (q.type === "single" && (!q.options || q.options.length < 2))
          throw new Error("Саволи " + (i + 1) + ": ҳадди ақал 2 вариант");
        if (q.type === "short" && !(q.correctText || q.correctAnswer))
          throw new Error("Саволи " + (i + 1) + ": ҷавоби дуруст лозим");
        if (q.type === "matching") {
          if (!q.leftItems || q.leftItems.length < 2)
            throw new Error("Саволи " + (i + 1) + ": мувофиқат — ҳадди ақал 2 банди чап (ҳар сатр)");
          if (!q.rightItems || q.rightItems.length < 1)
            throw new Error("Саволи " + (i + 1) + ": мувофиқат — бандҳои рост лозим");
          var pairKeys = q.pairs ? Object.keys(q.pairs) : [];
          if (!pairKeys.length)
            throw new Error("Саволи " + (i + 1) + ": ҷавоби дуруст лозим (ҷуфтҳо, масалан 1-1, 2-2)");
        }
      }
      var showRes = !!(document.getElementById("olyShowResults") || {}).checked;
      var payload = {
        title: title,
        type: (document.getElementById("olyType") || {}).value || "olympiad",
        passScore: Number((document.getElementById("olyPass") || {}).value) || 70,
        startTime: (document.getElementById("olyStart") || {}).value || null,
        endTime: (document.getElementById("olyEnd") || {}).value || null,
        isActive: !!(document.getElementById("olyActive") || {}).checked,
        showResultsToStudents: showRes,
        durationMin: (function () {
          var el = document.getElementById("olyDurationMin");
          if (!el || el.value === "") return 60;
          var n = Number(el.value);
          if (isNaN(n) || n < 0) return 60;
          return Math.floor(n);
        })(),
        questions: questions,
      };
      var data = await api("/api/admin/olympiads", { method: "POST", body: JSON.stringify(payload) });
      var saved = data.olympiad || data;
      await saveLocalCopy(payload, saved);
      if (msg) {
        msg.textContent = "Сабт шуд. Нусха .html/.txt ба Downloads.";
        msg.classList.remove("hidden", "error");
        msg.classList.add("ok");
      }
      var form = document.getElementById("olympiadForm");
      if (form) form.reset();
      if (listEl()) listEl().innerHTML = "";
      qSeq = 0;
      if (typeof window.loadOlympiads === "function") window.loadOlympiads();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message || String(err);
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(err.message || String(err));
    } finally {
      lock = false;
    }
    return false;
  }

  function wire() {
    var form = document.getElementById("olympiadForm");
    if (form) {
      form.setAttribute("action", "javascript:void(0)");
      form.setAttribute("onsubmit", "return false;");
      form.onsubmit = function (ev) {
        if (ev) {
          ev.preventDefault();
          ev.stopPropagation();
        }
        onSubmit(ev);
        return false;
      };
      form.addEventListener(
        "submit",
        function (ev) {
          ev.preventDefault();
          ev.stopImmediatePropagation();
          onSubmit(ev);
        },
        true
      );
    }
    var saveBtn = document.getElementById("btnSaveOlympiad");
    if (saveBtn) {
      saveBtn.type = "button";
      saveBtn.onclick = function (ev) {
        if (ev) {
          ev.preventDefault();
          ev.stopPropagation();
        }
        onSubmit(ev);
      };
    }
    [
      ["addQSingle", "single"],
      ["addQShort", "short"],
      ["addQMatch", "matching"],
      ["addQText", "text"],
    ].forEach(function (pair) {
      var el = document.getElementById(pair[0]);
      if (el)
        el.onclick = function (ev) {
          ev.preventDefault();
          addQuestion(pair[1]);
        };
    });
    var legacy = document.getElementById("addQuestionBtn");
    if (legacy)
      legacy.onclick = function (ev) {
        ev.preventDefault();
        addQuestion("single");
      };
  }

  window.__geoAddOlympiadQuestion = addQuestion;
  window.__geoSaveOlympiad = onSubmit;
  wire();
  document.querySelectorAll(".tab").forEach(function (b) {
    b.addEventListener("click", function () {
      if (b.getAttribute("data-tab") === "olympiads") setTimeout(wire, 30);
    });
  });
})();
