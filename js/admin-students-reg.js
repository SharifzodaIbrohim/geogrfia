/* admin-students-reg loader — plain body halves */
(function () {
  Promise.all([
    fetch("/js/admin-students-reg-body-a.js", { credentials: "same-origin" }).then(function (r) { if (!r.ok) throw new Error("a "+r.status); return r.text(); }),
    fetch("/js/admin-students-reg-body-b.js", { credentials: "same-origin" }).then(function (r) { if (!r.ok) throw new Error("b "+r.status); return r.text(); })
  ]).then(function (parts) {
    (0, eval)(parts[0] + parts[1]);
  }).catch(function (e) {
    console.error("[students-reg] load failed", e);
  });
})();
