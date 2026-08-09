(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function loadAudit() {
    try {
      var r = await fetch('/api/admin/audit?limit=80', {
        headers: { 'X-Admin-Token': tok() },
      });
      var d = await r.json();
      var body = document.getElementById('auditBody');
      if (!body) return;
      var rows = d.logs || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (x) {
              return (
                '<tr><td>' +
                esc(String(x.createdAt || '').slice(0, 19)) +
                '</td><td>' +
                esc(x.adminLogin) +
                '</td><td>' +
                esc(x.action) +
                '</td><td>' +
                esc((x.targetType || '') + ' ' + (x.targetId || '')) +
                '</td><td>' +
                esc(x.ip || '') +
                '</td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="5">Холӣ</td></tr>';
    } catch (e) {
      console.warn(e);
    }
  }
  async function loadNotifs() {
    try {
      var r = await fetch('/api/admin/notifications?limit=40', {
        headers: { 'X-Admin-Token': tok() },
      });
      var d = await r.json();
      var body = document.getElementById('notifBody');
      if (!body) return;
      var rows = d.notifications || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (x) {
              return (
                '<tr><td>' +
                esc(String(x.createdAt || '').slice(0, 19)) +
                '</td><td>' +
                esc(x.title) +
                '</td><td>' +
                esc(x.body) +
                '</td><td>' +
                (x.isRead ? '✓' : '•') +
                '</td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="4">Холӣ</td></tr>';
    } catch (e) {}
  }
  function ensureTab() {
    var nav = document.querySelector('nav.tabs');
    if (!nav || document.querySelector('[data-tab="audit"]')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tab';
    btn.dataset.tab = 'audit';
    btn.textContent = 'Audit / Огоҳӣ';
    nav.appendChild(btn);
    var main = document.querySelector('main.panel');
    if (!main || document.getElementById('tab-audit')) return;
    var sec = document.createElement('section');
    sec.id = 'tab-audit';
    sec.className = 'tab-panel hidden';
    sec.innerHTML =
      '<h2>Audit Log</h2>' +
      '<div style="margin-bottom:0.5rem;display:flex;gap:0.5rem;flex-wrap:wrap">' +
      '<button type="button" class="btn" id="refreshAuditBtn">Навсозӣ</button>' +
      '<button type="button" class="btn" id="testNotifBtn">Тести огоҳӣ</button></div>' +
      '<div class="table-wrap"><table><thead><tr><th>Вақт</th><th>Админ</th><th>Амал</th><th>Target</th><th>IP</th></tr></thead>' +
      '<tbody id="auditBody"></tbody></table></div>' +
      '<h3>Огоҳиҳо (in-app)</h3>' +
      '<div class="table-wrap"><table><thead><tr><th>Вақт</th><th>Унвон</th><th>Матн</th><th>Хонда</th></tr></thead>' +
      '<tbody id="notifBody"></tbody></table></div>';
    main.appendChild(sec);
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (b) {
        b.classList.remove('active');
      });
      document.querySelectorAll('.tab-panel').forEach(function (p) {
        p.classList.add('hidden');
      });
      btn.classList.add('active');
      sec.classList.remove('hidden');
      loadAudit();
      loadNotifs();
    });
    var ra = document.getElementById('refreshAuditBtn');
    if (ra)
      ra.addEventListener('click', function () {
        loadAudit();
        loadNotifs();
      });
    var tn = document.getElementById('testNotifBtn');
    if (tn)
      tn.addEventListener('click', function () {
        fetch('/api/admin/notifications/test', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Admin-Token': tok(),
          },
          body: '{}',
        })
          .then(function (r) {
            return r.json().then(function (d) {
              if (!r.ok) throw new Error(d.error || 'Хато');
              loadNotifs();
              alert('Огоҳӣ сохта шуд');
            });
          })
          .catch(function (e) {
            alert(e.message);
          });
      });
  }
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', ensureTab);
  else ensureTab();
})();
