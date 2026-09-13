/* admin-students-reg — single full base64 + TextDecoder (UTF-8 safe) */
(function () {
  fetch("/_asr_full.txt", { credentials: "same-origin", cache: "no-store" })
    .then(function (r) {
      if (!r.ok) throw new Error("_asr_full.txt " + r.status);
      return r.text();
    })
    .then(function (b64) {
      b64 = b64.replace(/\s+/g, "");
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
