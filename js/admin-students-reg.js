/* admin-students-reg — 4 plain UTF-8 parts */
(function () {
  var paths = ["/js/_asr_body_0.js", "/js/_asr_body_1.js", "/js/_asr_body_2.js", "/js/_asr_body_3.js"];
  Promise.all(paths.map(function (f) {
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
