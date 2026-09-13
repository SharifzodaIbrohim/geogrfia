/* admin-students-reg — load known-good body from jsDelivr @b272cc85 */
(function () {
  var BASE = "https://cdn.jsdelivr.net/gh/SharifzodaIbrohim/geogrfia@b272cc856ee5b329cbf658a6f3984ceb963a55b9";
  var F = [];
  for (var i = 0; i < 24; i++) F.push(BASE + "/_asr_x" + i + ".txt");
  Promise.all(
    F.map(function (f) {
      return fetch(f, { cache: "no-store" }).then(function (r) {
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
