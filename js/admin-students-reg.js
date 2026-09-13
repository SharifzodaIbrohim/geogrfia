/* admin-students-reg — 3 plain parts */
(function () {
  var F = ["/_asr_p0.js", "/_asr_p1.js", "/_asr_p2.js"];
  Promise.all(F.map(function (f) {
    return fetch(f, { credentials: "same-origin", cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(f + " " + r.status);
      return r.text();
    });
  })).then(function (parts) {
    (0, eval)(parts.join(""));
  }).catch(function (e) {
    console.error("[students-reg] load failed", e);
  });
})();
