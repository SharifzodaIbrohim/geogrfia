/**
 * P1.1 — Admin panel session via HttpOnly cookie.
 * Load AFTER admin.js. Forces credentials:include and clears legacy tokens.
 */
(function () {
  try {
    localStorage.removeItem('geo_admin_token');
  } catch (_) {}

  var _fetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    init = init || {};
    if (init.credentials === undefined) {
      init.credentials = 'include';
    }
    return _fetch(input, init);
  };
})();
