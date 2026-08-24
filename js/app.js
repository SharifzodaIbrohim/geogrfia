/* Temporary bootstrap: load full app.js from current live deployment (Render still has good copy).
 * After deploy of fix-country-count.js this keeps countries working.
 * Replace with full app.js content when convenient.
 */
(function () {
  var s = document.createElement('script');
  s.src = 'https://geografia-19tf.onrender.com/js/app.js?v=' + Date.now();
  s.defer = true;
  s.onerror = function () {
    console.error('Failed to load live app.js bootstrap');
  };
  document.head.appendChild(s);
})();
