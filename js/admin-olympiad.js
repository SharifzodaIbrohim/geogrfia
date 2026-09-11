/** admin-olympiad.js — known-good CDN body + matching overlay */
(function () {
  var URLS = [
    'https://cdn.jsdelivr.net/gh/SharifzodaIbrohim/geogrfia@24f6c636/js/admin-olympiad.js',
    'https://cdn.jsdelivr.net/gh/SharifzodaIbrohim/geogrfia@1456c879/js/admin-olympiad.js'
  ];
  function run(src) {
    try {
      (0, eval)(src);
      console.log('[admin-olympiad] body loaded');
    } catch (e) {
      console.error('[admin-olympiad] eval', e);
    }
    var s = document.createElement('script');
    s.src = 'js/admin-matching-simple.js?v=' + Date.now();
    document.head.appendChild(s);
  }
  function tryLoad(i) {
    if (i >= URLS.length) {
      console.error('[admin-olympiad] all CDNs failed');
      return;
    }
    fetch(URLS[i] + '?v=' + Date.now())
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then(run)
      .catch(function () { tryLoad(i + 1); });
  }
  tryLoad(0);
})();
