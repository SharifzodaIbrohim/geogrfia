/* student.js — CDN base exam logic; dark short/matching styles in css/student.css */
(function () {
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/gh/SharifzodaIbrohim/geogrfia@9034c95b6a7b/js/student.js';
  s.onerror = function () {
    console.error('student CDN load failed');
    var el = document.getElementById('loginError') || document.body;
    if (el) el.textContent = 'Саҳифаро навсозӣ кунед (JS)';
  };
  document.head.appendChild(s);
})();
