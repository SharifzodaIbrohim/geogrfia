/* admin-students-reg — 2 plain parts (UTF-8) */
(function () {
  Promise.all([
    fetch("/js/_asr_body_0.js", { credentials: "same-origin", cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("body0 " + r.status);
      return r.text();
    }),
    fetch("/js/_asr_body_1.js", { credentials: "same-origin", cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("body1 " + r.status);
      return r.text();
    })
  ]).then(function (parts) {
    (0, eval)(parts[0] + parts[1]);
  }).catch(function (e) {
    console.error("[students-reg] load failed", e);
  });
})();
