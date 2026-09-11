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

  function updateTotalScore() {
    var cards = listEl() ? listEl().querySelectorAll(".question-card") : [];
    var t = 0;
    cards.forEach(function (c) {
      var inp = c.querySelector(".q-maxscore");
      var n = inp ? Number(inp.value) : 1;
      if (isNaN(n) || n < 0) n = 1;
      t += n;
    });
    var bar = document.getElementById("olyTotalScoreBar");
    if (!bar && listEl()) {
      bar = document.createElement("div");
      bar.id = "olyTotalScoreBar";
      bar.className = "card";
      bar.style.cssText = "margin:.5rem 0;padding:.5rem .75rem;font-weight:600";
      listEl().parentNode.insertBefore(bar, listEl());
    }
    if (bar) bar.textContent = "Ҷамъи холҳо: " + (Math.round(t * 100) / 100);
  }

  var TYPE_LABEL = {
    single: "Интихоб (A–D)",
    short: "Ҷавоби кӯтоҳ",
    matching: "Мувофиқат",
    text: "Шарҳ / мафҳум",
  };

  function optRow(name, checked, val) {
    return (
      '<div class="q-opt-row" style="display:flex;gap:.4rem;align-items:center;margin:.25rem 0">' +
      '<input type="radio" name="' +
      esc(name) +
      '" ' +
      (checked ? "checked " : "") +
      '/>' +
      '<input type="text" class="q-opt" value="' +
      esc(val || "") +
      '" placeholder="Вариант" style="flex:1" />' +
      '<button type="button" class="btn small danger rm-opt">×</button></div>'
    );
  }

  function singleBody(pre) {
    var opts = (pre && pre.options) || ["", "", "", ""];
    while (opts.length < 2) opts.push("");
    var name = "ans_" + qSeq;
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
      '<label style="display:block;margin-top:.35rem">Ҷуфтҳо (ихтиёрӣ; холӣ=1-1,2-2…) <input class="q-pairs" style="width:100%" value="' +
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

  function wireScoreField(card) {
    var inp = card.querySelector(".q-maxscore");
    if (!inp) return;
    function sync() {
      var n = Number(inp.value);
      var lab = card.querySelector(".q-score-label");
      if (lab) lab.textContent = "Хол: " + (isNaN(n) ? "—" : n);
      updateTotalScore();
    }
    inp.addEventListener("input", sync);
    inp.addEventListener("change", sync);
  }

  function readMaxScore(card, fallback) {
    var inp = card.querySelector(".q-maxscore");
    var n = inp ? Number(inp.value) : NaN;
    if (isNaN(n) || n < 0) n = fallback != null ? fallback : 1;
    if (n < 0.5) n = 0.5;
    return Math.round(n * 100) / 100;
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

  function addQuestion(type, prefill) {
    var list = listEl();
    if (!list) return;
    qSeq += 1;
    var card = document.createElement("div");
    card.className = "question-card card";
    card.setAttribute("data-type", type);
    card.style.cssText = "margin-bottom:.75rem;padding:.75rem";
    var body =
      type === "single"
        ? singleBody(prefill)
        : type === "short"
        ? shortBody(prefill)
        : type === "matching"
        ? matchBody(prefill)
        : textBody(prefill);
    card.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem">' +
      "<strong>Савол · " +
      esc(TYPE_LABEL[type] || type) +
      "</strong>" +
      '<button type="button" class="btn small danger q-remove">×</button></div>' +
      scoreField(prefill, type) +
      body;
    list.appendChild(card);
    wireScoreField(card);
    updateTotalScore();

    var addOpt = card.querySelector(".add-opt");
    if (addOpt) {
      addOpt.onclick = function () {
        var box = card.querySelector(".q-options");
        var name = "ans_" + qSeq;
        box.insertAdjacentHTML("beforeend", optRow(name, false, ""));
        wireRmOpts(card);
      };
    }
    wireRmOpts(card);
    card.querySelector(".q-remove").onclick = function () {
      card.remove();
      updateTotalScore();
    };
  }

  function wireRmOpts(card) {
    card.querySelectorAll(".rm-opt").forEach(function (b) {
      b.onclick = function () {
        var rows = card.querySelectorAll(".q-opt-row");
        if (rows.length <= 2) return;
        b.closest(".q-opt-row").remove();
      };
    });
  }

  function collectQuestions() {
    var cards = listEl() ? listEl().querySelectorAll(".question-card") : [];
    var out = [];
    cards.forEach(function (card, i) {
      var type = card.getAttribute("data-type") || "single";
      var textEl = card.querySelector(".q-text");
      var text = textEl ? String(textEl.value || textEl.textContent || "").trim() : "";
      if (type === "single") {
        var opts = [];
        var ans = 0;
        card.querySelectorAll(".q-opt-row").forEach(function (row, j) {
          var inp = row.querySelector(".q-opt");
          var rad = row.querySelector('input[type="radio"]');
          opts.push(inp ? String(inp.value || "").trim() : "");
          if (rad && rad.checked) ans = j;
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
        if (!pairs || !Object.keys(pairs).length) {
          pairs = {};
          for (var pi = 0; pi < left.length; pi++) pairs[String(pi)] = pi;
          pairsText = pairsText || left.map(function (_x, ix) { return (ix + 1) + "-" + (ix + 1); }).join(", ");
        }
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
          body += "<p>Ҷавоб: " + esc(q.correctText || "—") + "</p>";
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
        return "<h3>" + (i + 1) + ". [" + esc(q.type) + "] " + body + "</h3>";
      })
      .join("\n");
    return (
      "<!DOCTYPE html><html><head><meta charset=utf-8><title>" +
      esc(payload.title || "olympiad") +
      "</title></head><body>" +
      "<h1>" +
      esc(payload.title || "") +
      "</h1>" +
      "<p>id=" +
      esc((saved && saved.id) || "") +
      " · саволҳо: " +
      qs.length +
      "</p>" +
      rows +
      "</body></html>"
    );
  }

  async function onSubmit(ev) {
    if (ev) {
      ev.preventDefault();
      ev.stopPropagation();
    }
    if (lock) return;
    var msg = document.getElementById("olyFormMsg");
    var title = (document.getElementById("olyTitle") || {}).value || "";
    title = String(title).trim();
    if (!title) {
      if (msg) {
        msg.textContent = "Унвон лозим аст";
        msg.classList.remove("hidden");
      }
      return;
    }
    var questions;
    try {
      questions = collectQuestions();
      questions.forEach(function (q, i) {
        if (!q.text) throw new Error("Саволи " + (i + 1) + ": матн холӣ");
        if (q.type === "single") {
          if (!q.options || q.options.filter(Boolean).length < 2)
            throw new Error("Саволи " + (i + 1) + ": ҳадди ақал 2 вариант");
        }
        if (q.type === "short" && !q.correctText)
          throw new Error("Саволи " + (i + 1) + ": ҷавоби дуруст лозим");
        if (q.type === "matching") {
          if (!q.leftItems || q.leftItems.length < 2)
            throw new Error("Саволи " + (i + 1) + ": мувофиқат — ҳадди ақал 2 банди чап (ҳар сатр)");
          if (!q.rightItems || q.rightItems.length < 1)
            throw new Error("Саволи " + (i + 1) + ": мувофиқат — бандҳои рост лозим");
        }
      });
    } catch (e) {
      if (msg) {
        msg.textContent = e.message || String(e);
        msg.classList.remove("hidden");
      } else alert(e.message || String(e));
      return;
    }
    if (!questions.length) {
      if (msg) {
        msg.textContent = "Ҳадди ақал 1 савол лозим";
        msg.classList.remove("hidden");
      }
      return;
    }
    var showRes = !!(document.getElementById("olyShowResults") || {}).checked;
    var pass = Number((document.getElementById("olyPass") || {}).value || 70);
    var durMin = Number((document.getElementById("olyDurationMin") || {}).value || 60);
    var payload = {
      title: title,
      type: (document.getElementById("olyType") || {}).value || "olympiad",
      passScore: pass,
      durationSec: Math.max(0, Math.round(durMin * 60)),
      startAt: (document.getElementById("olyStart") || {}).value || null,
      endAt: (document.getElementById("olyEnd") || {}).value || null,
      active: !!(document.getElementById("olyActive") || {}).checked,
      showResultsToStudents: showRes,
      questions: questions,
    };
    lock = true;
    try {
      var saved = await api("/api/admin/olympiads", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (msg) {
        msg.textContent = "Сабт шуд · id=" + (saved.id || saved.olympiadId || "");
        msg.classList.remove("hidden");
      }
      try {
        forceDownload(
          safeName(title) + ".html",
          buildLocalHtml(payload, saved),
          "text/html;charset=utf-8"
        );
      } catch (e) {}
      if (typeof window.loadOlympiads === "function") window.loadOlympiads();
    } catch (e) {
      if (msg) {
        msg.textContent = e.message || String(e);
        msg.classList.remove("hidden");
      } else alert(e.message || String(e));
    } finally {
      lock = false;
    }
  }

  function wire() {
    var form = document.getElementById("olympiadForm");
    if (form) {
      form.onsubmit = function (ev) {
        ev.preventDefault();
        onSubmit(ev);
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

/* auto-load matching helper */
(function(){try{var s=document.createElement('script');s.src='js/admin-matching-simple.js?v=2';document.head.appendChild(s);}catch(e){}})();
