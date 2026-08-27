/* admin-olympiad.js — loader joins _ao0.._ao2 base64 plain (not zlib) */
(function () {
  var N = 3, parts = [], i = 0;
  function go() {
    if (i >= N) return done();
    fetch("js/_ao" + i + ".txt")
      .then(function (r) { if (!r.ok) throw new Error("chunk " + i); return r.text(); })
      .then(function (t) { parts.push(t.trim()); i++; go(); })
      .catch(function (e) { console.error("admin-olympiad load", e); });
  }
  function done() {
    var b64 = parts.join("");
    while (b64.length % 4) b64 += "=";
    var bin = atob(b64), u = new Uint8Array(bin.length);
    for (var j = 0; j < bin.length; j++) u[j] = bin.charCodeAt(j);
    var src = new TextDecoder("utf-8").decode(u);
    var s = document.createElement("script");
    s.text = src;
    (document.body || document.documentElement).appendChild(s);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
  else go();
})();
