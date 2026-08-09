(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function ensureTab() {
    var nav = document.querySelector('nav.tabs');
    if (!nav || document.querySelector('[data-tab="gmail"]')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tab';
    btn.dataset.tab = 'gmail';
    btn.textContent = 'Gmail корбарон';
    nav.appendChild(btn);
    var main = document.querySelector('main.panel');
    if (!main) return;
    var sec = document.createElement('section');
    sec.id = 'tab-gmail';
    sec.className = 'tab-panel hidden';
    sec.innerHTML =
      '<h2>Мониторинги корбарони Gmail (оддӣ)</h2>' +
      '<p class="muted">Аз хонандагони ID ҷудо. Филтр: мактаб / минтақа / ҷинс</p>' +
      '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin:0.5rem 0">' +
      '<input id="gmSchool" placeholder="Мактаб" /><input id="gmRegion" placeholder="Минтақа" />' +
      '<select id="gmGender"><option value="">Ҷинс</option><option value="male">Писар</option><option value="female">Духтар</option></select>' +
      '<button type="button" class="btn primary" id="gmFilter">Филтр</button></div>' +
      '<div class="table-wrap"><table><thead><tr>' +
      '<th>Ном</th><th>Email</th><th>Ҷинс</th><th>Синф</th><th>Мактаб</th><th>Минтақа</th>' +
      '<th>Супориш</th><th>Гузашт</th><th>Нагузашт</th></tr></thead><tbody id="gmBody"></tbody></table></div>';
    main.appendChild(sec);
    async function load() {
      var q = new URLSearchParams();
      var s = document.getElementById('gmSchool').value.trim();
      if (s) q.set('school', s);
      var r = document.getElementById('gmRegion').value.trim();
      if (r) q.set('region', r);
      var g = document.getElementById('gmGender').value;
      if (g) q.set('gender', g);
      var res = await fetch('/api/admin/gmail-users?' + q.toString(), {
        headers: { 'X-Admin-Token': tok() },
      });
      var d = await res.json();
      var body = document.getElementById('gmBody');
      var rows = d.users || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (u) {
              var st = u.stats || {};
              var gen = u.gender === 'male' ? 'Писар' : u.gender === 'female' ? 'Духтар' : '—';
              return (
                '<tr><td>' +
                esc(u.name) +
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
                (st.attempts || 0) +
                '</td><td>' +
                (st.passed || 0) +
                '</td><td>' +
                (st.failed || 0) +
                '</td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="9">Холӣ</td></tr>';
    }
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (b) {
        b.classList.remove('active');
      });
      document.querySelectorAll('.tab-panel').forEach(function (p) {
        p.classList.add('hidden');
      });
      btn.classList.add('active');
      sec.classList.remove('hidden');
      load();
    });
    var f = document.getElementById('gmFilter');
    if (f) f.addEventListener('click', load);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ensureTab);
  else ensureTab();
})();
