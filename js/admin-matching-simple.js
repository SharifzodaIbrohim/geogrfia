/** Matching simplify overlay — auto pairs + partial score hint */
(function () {
  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }
  ready(function () {
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      if (tries > 40) { clearInterval(t); return; }
      var form = document.getElementById('olympiadForm') || document.querySelector('#tab-olympiads form, form');
      if (!form) return;
      clearInterval(t);
      form.addEventListener('submit', function () {
        document.querySelectorAll('.question-card').forEach(function (card) {
          var leftEl = card.querySelector('.q-left');
          if (!leftEl) return;
          var left = String(leftEl.value || '')
            .split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
          var pairsInp = card.querySelector('.q-pairs');
          if (pairsInp && !String(pairsInp.value || '').trim() && left.length) {
            pairsInp.value = left.map(function (_, i) { return (i + 1) + '-' + (i + 1); }).join(', ');
          }
          var maxInp = card.querySelector('.q-maxscore');
          if (maxInp && (!maxInp.value || Number(maxInp.value) < 0.5) && left.length) {
            maxInp.value = String(left.length);
          }
        });
      }, true);
      console.log('[matching-overlay] ready');
    }, 250);
  });
})();
