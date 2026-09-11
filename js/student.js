/** Student portal loader — joins plain parts then eval */
(function () {
  var parts = [];
  var n = 4;
  var loaded = 0;
  function go() {
    if (loaded < n) return;
    var code = parts.join('');
    try {
      (0, eval)(code);
    } catch (e) {
      console.error('student.js load failed', e);
      var el = document.getElementById('loginError') || document.body;
      if (el) el.textContent = (el.textContent || '') + ' [JS: ' + (e.message || e) + ']';
    }
  }
  for (var i = 0; i < n; i++) {
    (function (idx) {
      fetch('/_st_p' + idx + '.txt?v=' + Date.now())
        .then(function (r) { if (!r.ok) throw new Error('part ' + idx + ' ' + r.status); return r.text(); })
        .then(function (t) { parts[idx] = t; loaded++; go(); })
        .catch(function (e) { console.error(e); });
    })(i);
  }
})();
