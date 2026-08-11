/**
 * P1.2 — Real logout helper (server revoke + cookie clear + client state).
 * Usage: window.geoLogout({ admin: true|false }).then(() => location.href = ...)
 */
(function (global) {
  async function geoLogout(opts) {
    opts = opts || {};
    var admin = !!opts.admin;
    var url = admin ? '/api/admin/logout' : '/api/auth/logout';
    try {
      await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (_) {}
    try {
      localStorage.removeItem('geo_admin_token');
      localStorage.removeItem('geo_admin_user');
      localStorage.removeItem('geo_user_token');
      localStorage.removeItem('userToken');
      localStorage.removeItem('geo_user');
      localStorage.removeItem('currentUser');
    } catch (_) {}
    return true;
  }
  global.geoLogout = geoLogout;
})(typeof window !== 'undefined' ? window : this);
