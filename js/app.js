/*! Geografia app.js — load full bundle from known-good historical commit */
(function () {
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/gh/SharifzodaIbrohim/geogrfia@d207de6ace34cf95781cc10544c7a1954a3fc7b4/js/app.js';
  s.defer = true;
  s.onerror = function () {
    console.error('Failed to load app.js from CDN');
  };
  document.head.appendChild(s);
})();
