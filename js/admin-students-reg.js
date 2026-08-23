/* admin-students-reg — 1-page Даватнома + black IG QR */
(function () {
  var FILES = ["/js/_asr_b64_00.txt", "/js/_asr_b64_01.txt", "/js/_asr_b64_02.txt"];
  Promise.all(FILES.map(function (f) {
    return fetch(f, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error(f + " " + r.status);
      return r.text();
    });
  })).then(function (parts) {
    var b64 = parts.join("").replace(/\s+/g, "");
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    var code = new TextDecoder("utf-8").decode(bytes);
    (0, eval)(code);
  }).catch(function (e) {
    console.error("[students-reg loader]", e);
  });
})();
