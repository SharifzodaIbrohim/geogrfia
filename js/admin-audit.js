(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  function hdr(json) {
    var h = {};
    if (json) h['Content-Type'] = 'application/json';
    var t = tok();
    if (t) h['X-Admin-Token'] = t;
    return h;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function loadAudit() {
    var body = document.getElementById('auditBody');
    if (!body) return;
    body.innerHTML = '<tr><td colspan="5">Бор мешавад…</td></tr>';
    try {
      var r = await fetch('/api/admin/audit?limit=80', {
        headers: hdr(),
        credentials: 'include',
      });
      var d = await r.json().catch(function () { return {}; });
      if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
      var rows = d.logs || d.items || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (x) {
              return (
                '<tr><td>' +
                esc(String(x.createdAt || x.created_at || '').slice(0, 19)) +
                '</td><td>' +
                esc(x.adminLogin || x.admin_login || '') +
                '</td><td>' +
                esc(x.action) +
                '</td><td>' +
                esc((x.targetType || x.target_type || '') + ' ' + (x.targetId || x.target_id || '')) +
                '</td><td>' +
                esc(x.ip || '') +
                '</td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="5">Холӣ</td></tr>';
    } catch (e) {
      body.innerHTML = '<tr><td colspan="5">' + esc(e.message) + '</td></tr>';
    }
  }
  async function loadNotifs() {
    var body = document.getElementById('notifBody');
    if (!body) return;
    try {
      var r = await fetch('/api/admin/notifications?limit=40', {
        headers: hdr(),
        credentials: 'include',
      });
      var d = await r.json().catch(function () { return {}; });
      if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
      var rows = d.notifications || d.items || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (x) {
              return (
                '<tr><td>' +
                esc(String(x.createdAt || x.created_at || '').slice(0, 19)) +
                '</td><td>' +
                esc(x.title) +
                '</td><td>' +
                esc(x.body) +
                '</td><td>' +
                (x.isRead || x.is_read ? '✓' : '•') +
                '</td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="4">Холӣ</td></tr>';
    } catch (e) {
      body.innerHTML = '<tr><td colspan="4">' + esc(e.message) + '</td></tr>';
    }
  }
  function loadAll() {
    loadAudit();
    loadNotifs();
  }
  function wire() {
    var ra = document.getElementById('refreshAuditBtn');
    if (ra && !ra._bound) {
      ra._bound = true;
      ra.addEventListener('click', loadAll);
    }
    var tn = document.getElementById('testNotifBtn');
    if (tn && !tn._bound) {
      tn._bound = true;
      tn.addEventListener('click', async function () {
        try {
          await fetch('/api/admin/notifications', {
            method: 'POST',
            headers: hdr(true),
            credentials: 'include',
            body: JSON.stringify({ title: 'Test', body: 'Огоҳии санҷишӣ' }),
          });
          loadNotifs();
        } catch (e) {
          alert(e.message);
        }
      });
    }
    document.querySelectorAll('.tab[data-tab="audit"]').forEach(function (btn) {
      if (btn._auBound) return;
      btn._auBound = true;
      btn.addEventListener('click', function () {
        setTimeout(loadAll, 30);
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
