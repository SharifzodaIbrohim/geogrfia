/**
 * P1.1 — Admin panel session via HttpOnly cookie.
 * Forces credentials:include on fetch. Keeps geo_admin_token for Bearer fallback
 * (cookie-only admin APIs are not fully wired on all routes yet).
 */
(function () {
  var _fetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    init = init || {};
    if (init.credentials === undefined) {
      init.credentials = "include";
    }
    return _fetch(input, init);
  };
})();
