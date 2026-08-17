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
        } catch (_) {}
        a.remove();
      }, 1200);
      return true;
    } catch (e) {
      console.error(e);
      return false;
    }
  }

  function safeName(s) {
    return String(s || "olympiad")
      .replace(/[\\/:*?"<>|]+/g, "_")
      .replace(/\s+/g, "_")
      .slice(0, 80);
  }

  function listEl() {
    return document.getElementById("questionsList");
  }

  function typeLabel(t) {
    return (
      {
        single: "Интихоби як ҷавоб (A–D)",
        short: "Ҷавоби кӯтоҳ / рақамӣ",
        matching: "Мувофиқат",
        text: "Шарҳ / мафҳум (матн)",
      }[t] || t
    );
  }

  function addOptionRow(box, name, val, checked) {
    var row = document.createElement("div");
    row.className = "opt-row";
    row.style.cssText = "display:flex;gap:.4rem;align-items:center;margin:.25rem 0";
    row.innerHTML =
      '<input type="radio" name="' +
      name +
      '" ' +
      (checked ? "checked" : "") +
      ' title="Ҷавоби дуруст" />' +
      '<input type="text" class="opt-text" placeholder="Вариант" value="' +
      esc(val || "") +
      '" style="flex:1" />' +
      '<button type="button" class="btn small danger opt-del">×</button>';
    row.querySelector(".opt-del").onclick = function () {
      if (box.querySelectorAll(".opt-row").length <= 2) {
        alert("Ҳадди ақал 2 вариант");
        return;
      }
      row.remove();
    };
    box.appendChild(row);
  }

  function buildSingleBody(n, pre) {
    var div = document.createElement("div");
    div.innerHTML =
      '<input class="q-text" placeholder="Матни савол" style="width:100%;margin:.35rem 0" value="' +
      esc((pre && pre.text) || "") +
      '" />' +
      '<div class="q-options"></div>' +
      '<button type="button" class="btn small add-opt">+ Вариант</button>' +
      '<p class="muted" style="font-size:.85rem;margin:.25rem 0">Радио = ҷавоби дуруст</p>';
    var box = div.querySelector(".q-options");
    var opts = (pre && pre.options) || ["", "", "", ""];
    var ans = pre && typeof pre.answer === "number" ? pre.answer : 0;
    opts.forEach(function (v, i) {
      addOptionRow(box, "correct-" + n, v, i === ans);
    });
    div.querySelector(".add-opt").onclick = function () {
      addOptionRow(box, "correct-" + n, "", false);
    };
    return div;
  }

  function buildShortBody(pre) {
    var div = document.createElement("div");
    div.innerHTML =
      '<textarea class="q-text" rows="2" placeholder="Матни савол" style="width:100%;margin:.35rem 0">' +
      esc((pre && pre.text) || "") +
      "</textarea>" +
      '<label>Ҷавоби дуруст (админ)<input class="q-correct" style="width:100%;margin-top:.25rem" placeholder="масалан: 42" value="' +
      esc((pre && pre.correctText) || "") +
      '" /></label>';
    return div;
  }

  function buildMatchingBody(pre) {
    var div = document.createElement("div");
    div.innerHTML =
      '<textarea class="q-text" rows="2" placeholder="Мувофиқатро муайян намоед" style="width:100%;margin:.35rem 0">' +
      esc((pre && pre.text) || "Мувофиқатро муайян намоед") +
      "</textarea>" +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">' +
      '<div><strong>Чап</strong><textarea class="q-left" rows="5" style="width:100%">' +
      esc(((pre && pre.leftItems) || []).join("\n")) +
      "</textarea></div>" +
      '<div><strong>Рост</strong><textarea class="q-right" rows="5" style="width:100%">' +
      esc(((pre && pre.rightItems) || []).join("\n")) +
      "</textarea></div></div>" +
      '<label style="display:block;margin-top:.5rem">Ҷуфтҳо (A=1,B=2)' +
      '<input class="q-pairs" style="width:100%;margin-top:.25rem" value="' +
      esc((pre && pre.pairsText) || "") +
      '" /></label>';
    return div;
  }

  function buildTextBody(pre) {
    var div = document.createElement("div");
    div.innerHTML =
      '<textarea class="q-text" rows="2" placeholder="Мафҳум" style="width:100%;margin:.35rem 0">' +
      esc((pre && pre.text) || "") +
      "</textarea>" +
      '<label>Калидҳо (ихтиёрӣ, | ҷудо)' +
      '<input class="q-correct" style="width:100%;margin-top:.25rem" value="' +
      esc((pre && pre.correctText) || "") +
      '" /></label>';
    return div;
  }

  function addQuestion(type, prefill) {
    var list = listEl();
    if (!list) return;
    type = type || "single";
    qSeq += 1;
    var n = qSeq;
    var wrap = document.createElement("div");
    wrap.className = "question-card card";
    wrap.dataset.q = String(n);
    wrap.dataset.type = type;
    wrap.style.cssText = "margin:.6rem 0;padding:.75rem;border:1px solid #ddd;border-radius:8px";
    wrap.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
      "<strong>Савол " +
      n +
      " — " +
      esc(typeLabel(type)) +
      "</strong>" +
      '<button type="button" class="btn small danger q-remove">×</button></div>';
    var body =
      type === "short"
        ? buildShortBody(prefill)
        : type === "matching"
          ? buildMatchingBody(prefill)
          : type === "text"
            ? buildTextBody(prefill)
            : buildSingleBody(n, prefill);
    wrap.appendChild(body);
    wrap.querySelector(".q-remove").onclick = function () {
      wrap.remove();
    };
    list.appendChild(wrap);
  }

  function parsePairs(text, leftLen) {
    var map = {};
    String(text || "")
      .split(/[,;]+/)
      .forEach(function (part) {
        var m = part.trim().match(/^([A-Za-zА-Яа-яЁё]|(\d+))\s*[=:]\s*(\d+)$/);
        if (!m) return;
        var left = m[1];
        var right = parseInt(m[3], 10) - 1;
        var li;
        if (/^\d+$/.test(left)) li = parseInt(left, 10) - 1;
        else li = left.toUpperCase().charCodeAt(0) - 65;
        if (li >= 0 && li < leftLen && right >= 0) map[String(li)] = right;
      });
    return map;
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
        out.push({ id: i + 1, type: "single", text: text, options: opts, answer: ans, maxScore: 1 });
      } else if (type === "short") {
        var c = card.querySelector(".q-correct");
        out.push({
          id: i + 1,
          type: "short",
          text: text,
          correctText: c ? String(c.value || "").trim() : "",
          maxScore: 1,
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
        out.push({
          id: i + 1,
          type: "matching",
          text: text,
          leftItems: left,
          rightItems: right,
          pairs: parsePairs(pairsText, left.length),
          pairsText: pairsText,
          maxScore: left.length || 1,
        });
      } else {
        var cc = card.querySelector(".q-correct");
        out.push({
          id: i + 1,
          type: "text",
          text: text,
          correctText: cc ? String(cc.value || "").trim() : "",
          maxScore: 1,
          manual: !(cc && String(cc.value || "").trim()),
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
      "<!DOCTYPE html><html lang=tg><head><meta charset=utf-8><title>" +
      esc(payload.title) +
      "</title></head><body><h1>" +
      esc(payload.title) +
      "</h1><p>Навъ: " +
      esc(payload.type) +
      " | Ҳад: " +
      payload.passScore +
      "% | Натиҷа: " +
      (payload.showResultsToStudents ? "ҳа" : "не") +
      "</p><p>ID: " +
      esc((saved && saved.id) || "") +
      "</p>" +
      rows +
      "</body></html>"
    );
  }

  function buildLocalTxt(payload, saved) {
    var lines = [
      "Унвон: " + payload.title,
      "ID: " + ((saved && saved.id) || ""),
      "Навъ: " + payload.type,
      "Ҳад: " + payload.passScore + "%",
      "Натиҷа: " + (payload.showResultsToStudents ? "ҳа" : "не"),
      "Сана: " + new Date().toISOString(),
      "",
    ];
    (payload.questions || []).forEach(function (q, i) {
      lines.push(i + 1 + ". [" + q.type + "] " + q.text);
      if (q.type === "single") {
        (q.options || []).forEach(function (o, j) {
          lines.push("   " + (j === q.answer ? "*" : "-") + " " + o);
        });
      } else {
        lines.push("   Ҷавоб: " + (q.correctText || q.pairsText || ""));
      }
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
      if (!questions.length) throw new Error("Ҳадди ақал 1 савол");
      for (var i = 0; i < questions.length; i++) {
        var q = questions[i];
        if (!q.text) throw new Error("Саволи " + (i + 1) + ": матн холӣ");
        if (q.type === "single" && (!q.options || q.options.length < 2))
          throw new Error("Саволи " + (i + 1) + ": ҳадди ақал 2 вариант");
        if (q.type === "short" && !q.correctText) throw new Error("Саволи " + (i + 1) + ": ҷавоби дуруст лозим");
        if (q.type === "matching" && (!q.leftItems || q.leftItems.length < 2))
          throw new Error("Саволи " + (i + 1) + ": мувофиқат");
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
      form.onsubmit = function (ev) {
        onSubmit(ev);
        return false;
      };
    }
    var saveBtn = document.getElementById("btnSaveOlympiad");
    if (saveBtn) {
      saveBtn.type = "button";
      saveBtn.onclick = function (ev) {
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
})();
