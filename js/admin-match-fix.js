/** Matching UX fix — auto pairs + simpler admin + no required pairs field */
(function () {
  function whenReady(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  function enhanceCards() {
    document.querySelectorAll(".question-card").forEach(function (card) {
      if (card.getAttribute("data-qtype") !== "matching") return;
      var pairs = card.querySelector(".q-pairs");
      if (pairs) {
        pairs.placeholder = "холӣ = 1→1, 2→2…";
        var lab = pairs.closest("label");
        if (lab && !lab.getAttribute("data-hinted")) {
          lab.setAttribute("data-hinted", "1");
          var hint = document.createElement("p");
          hint.className = "muted";
          hint.style.cssText = "margin:.25rem 0;font-size:.85rem";
          hint.innerHTML =
            "Содда: сатри 1и <b>Чап</b> = сатри 1и <b>Рост</b>. Хол = шумораи ҷуфтҳо (ҳар ҷуфт 1 хол).";
          lab.parentNode.insertBefore(hint, lab);
        }
      }
      var left = card.querySelector(".q-left");
      var ms = card.querySelector(".q-maxscore");
      function syncScore() {
        if (!left || !ms) return;
        var n = String(left.value || "")
          .split("\n")
          .map(function (s) { return s.trim(); })
          .filter(Boolean).length;
        if (n > 0 && (!ms.dataset.userSet || ms.value === "" || ms.value === "1")) {
          ms.value = String(n);
          var lbl = card.querySelector(".q-score-label");
          if (lbl) lbl.textContent = "Хол: " + n;
        }
      }
      if (left && !left.getAttribute("data-msync")) {
        left.setAttribute("data-msync", "1");
        left.addEventListener("input", syncScore);
        syncScore();
      }
      if (ms && !ms.getAttribute("data-userlisten")) {
        ms.setAttribute("data-userlisten", "1");
        ms.addEventListener("change", function () {
          ms.dataset.userSet = "1";
        });
      }
    });
  }

  whenReady(function () {
    enhanceCards();
    var list = document.getElementById("questionsList");
    if (list && window.MutationObserver) {
      new MutationObserver(function () {
        enhanceCards();
      }).observe(list, { childList: true, subtree: true });
    }

    document.addEventListener(
      "click",
      function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var btn = t.closest("#olySaveBtn, #olyCreateBtn, button[data-save-olympiad]");
        if (!btn) return;
        document.querySelectorAll(".question-card").forEach(function (card) {
          if (card.getAttribute("data-qtype") !== "matching") return;
          var left = String((card.querySelector(".q-left") || {}).value || "")
            .split("\n")
            .map(function (s) { return s.trim(); })
            .filter(Boolean);
          var right = String((card.querySelector(".q-right") || {}).value || "")
            .split("\n")
            .map(function (s) { return s.trim(); })
            .filter(Boolean);
          var pairsEl = card.querySelector(".q-pairs");
          if (pairsEl && !String(pairsEl.value || "").trim()) {
            var n = Math.min(left.length, right.length);
            var parts = [];
            for (var i = 0; i < n; i++) parts.push(i + 1 + "-" + (i + 1));
            pairsEl.value = parts.join(", ");
          }
          var ms = card.querySelector(".q-maxscore");
          if (ms && left.length && (ms.value === "" || Number(ms.value) < 0.5)) {
            ms.value = String(left.length);
          }
        });
      },
      true
    );
  });
})();
