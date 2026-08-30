/* admin-students-reg loader — loads full body from single plain JS file */
(function () {
  fetch("/js/admin-students-reg-body.js", { credentials: "same-origin" })
    .then(function (r) {
      if (!r.ok) throw new Error("body " + r.status);
      return r.text();
    })
    .then(function (text) {
      (0, eval)(text);
    })
    .catch(function (e) {
      console.error("[students-reg] load failed", e);
    });
})();
