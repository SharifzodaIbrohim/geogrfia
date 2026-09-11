/** Restore classic review from known-good commit (1456c879) — unbreak SEE_FILE */
(function () {
  function boot(code) {
    try { (0, eval)(code); }
    catch (e) { console.error('[admin-results-review] restore eval failed', e); }
  }
  var urls = [
    'https://cdn.jsdelivr.net/gh/SharifzodaIbrohim/geogrfia@1456c879/js/admin-results-review.js',
    'https://raw.githubusercontent.com/SharifzodaIbrohim/geogrfia/1456c879/js/admin-results-review.js'
  ];
  var i = 0;
  function next() {
    if (i >= urls.length) {
      console.error('[admin-results-review] all restore sources failed');
      return;
    }
    var url = urls[i++];
    fetch(url, { cache: 'no-store', credentials: 'omit' })
      .then(function (r) {
        if (!r.ok) throw new Error(String(r.status));
        return r.text();
      })
      .then(boot)
      .catch(function () { next(); });
  }
  next();
})();
