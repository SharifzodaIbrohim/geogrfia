/** admin-matching-simple.js — auto 1-1 pairs + softer save for matching */
(function () {
  function patch() {
    if (typeof window.__geoAddOlympiadQuestion !== 'function') return;

    // Capture-phase: before save, fill empty pair fields with identity 1-1, 2-2…
    document.addEventListener('click', function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      if (t.id !== 'btnSaveOlympiad' && !(t.closest && t.closest('#btnSaveOlympiad'))) return;
      document.querySelectorAll('.question-card[data-type="matching"]').forEach(function (card) {
        var left = String((card.querySelector('.q-left') || {}).value || '')
          .split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
        var pairsInp = card.querySelector('.q-pairs');
        if (!pairsInp) return;
        if (String(pairsInp.value || '').trim()) return;
        pairsInp.value = left.map(function (_x, i) { return (i + 1) + '-' + (i + 1); }).join(', ');
      });
    }, true);

    function hint() {
      document.querySelectorAll('.question-card[data-type="matching"]').forEach(function (card) {
        if (card.querySelector('.match-hint')) return;
        var p = document.createElement('p');
        p.className = 'muted match-hint';
        p.style.cssText = 'font-size:.85rem;margin:.25rem 0';
        p.textContent = 'Ҷуфтҳо холӣ → худкор 1→1, 2→2… Хол = ҳар ҷуфти дуруст (масалан 4/4→4, 3/4→3).';
        var pairs = card.querySelector('.q-pairs');
        if (pairs && pairs.parentNode) pairs.parentNode.insertBefore(p, pairs);
      });
    }
    setInterval(hint, 800);
    console.log('[matching-simple] auto 1-1 on save installed');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', patch);
  else patch();
})();
