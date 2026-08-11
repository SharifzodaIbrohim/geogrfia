(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  function hdr() {
    var h = {};
    var t = tok();
    if (t) h['X-Admin-Token'] = t;
    return h;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function load() {
    var body = document.getElementById('gmBody');
    if (!body) return;
    var q = new URLSearchParams();
    var sEl = document.getElementById('gmSchool');
    var rEl = document.getElementById('gmRegion');
    var gEl = document.getElementById('gmGender');
    if (sEl && sEl.value.trim()) q.set('school', sEl.value.trim());
    if (rEl && rEl.value.trim()) q.set('region', rEl.value.trim());
    if (gEl && gEl.value) q.set('gender', gEl.value);
    body.innerHTML = '<tr><td colspan="10">Бор мешавад…</td></tr>';
    try {
      var res = await fetch('/api/admin/gmail-users?' + q.toString(), {
        headers: hdr(),
        credentials: 'include',
      });
      var d = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(d.error || ('HTTP ' + res.status));
      var rows = d.users || d.items || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (u) {
              var st = u.stats || {};
              var gen = u.gender === 'male' ? 'Писар' : u.gender === 'female' ? 'Духтар' : '—';
              return (
                '<tr><td>' +
                esc(u.name || u.fullName) +
                '</td><td>' +
                esc(u.email) +
                '</td><td>' +
                gen +
                '</td><td>' +
                esc(u.className || '') +
                '</td><td>' +
                esc(u.school || '') +
                '</td><td>' +
                esc(u.region || '') +
                '</td><td>' +
                (u.rating || 1200) +
                '</td><td>' +
                (st.attempts || 0) +
                '</td><td>' +
                (st.passed || 0) +
                '</td><td>' +
                (st.failed || 0) +
                '</td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="10">Холӣ</td></tr>';
    } catch (e) {
      body.innerHTML = '<tr><td colspan="10">' + esc(e.message) + '</td></tr>';
    }
  }

  function wire() {
    var f = document.getElementById('gmFilter');
    if (f && !f._gmBound) {
      f._gmBound = true;
      f.addEventListener('click', load);
    }
    document.querySelectorAll('.tab[data-tab="gmail"]').forEach(function (btn) {
      if (btn._gmBound) return;
      btn._gmBound = true;
      btn.addEventListener('click', function () {
        setTimeout(load, 30);
      });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
