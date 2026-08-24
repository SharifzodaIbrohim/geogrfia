/*! Geografia app.js materializer */
(function () {
  var NEED = 18;
  function go() {
    var p = window.__APP_B64 || [];
    if ((window.__APP_LOADED || 0) < NEED) return;
    for (var i = 0; i < NEED; i++) if (!p[i]) return;
    try {
      var b64 = p.join('');
      var bin = atob(b64);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      if (typeof DecompressionStream === 'undefined') {
        console.error('No DecompressionStream');
        return;
      }
      var ds = new DecompressionStream('deflate');
      new Response(new Blob([bytes]).stream().pipeThrough(ds)).arrayBuffer().then(function (buf) {
        var code = new TextDecoder().decode(buf);
        (0, eval)(code);
      }).catch(function (e) { console.error('app inflate', e); });
    } catch (e) { console.error('app materialize', e); }
  }
  window.__APP_LOADED = 0;
  for (var i = 0; i < NEED; i++) {
    (function (i) {
      var s = document.createElement('script');
      s.src = 'js/_app_b64_' + i + '.js';
      s.onload = function () { window.__APP_LOADED++; go(); };
      s.onerror = function () { console.error('_app_b64_' + i + ' failed'); };
      document.head.appendChild(s);
    })(i);
  }
})();
