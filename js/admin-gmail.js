(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
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
    try {
      var res = await fetch('/api/admin/gmail-users?' + q.toString(), {
        headers: { 'X-Admin-Token': tok() },
      });
      var d = await res.json();
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

  function ensureTab() {
    var nav = document.querySelector('nav.tabs');
    var main = document.querySelector('main.panel');
    if (nav && !document.querySelector('[data-tab="gmail"]')) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'tab';
      btn.dataset.tab = 'gmail';
      btn.textContent = 'Gmail корбарон';
      nav.appendChild(btn);
    }
    if (main && !document.getElementById('tab-gmail')) {
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
        '<th>Ном</th><th>Email</th><th>Ҷинс</th><th>Синф</th><th>Мактаб</th><th>Минтақа</th><th>Rating</th>' +
        '<th>Супориш</th><th>Гузашт</th><th>Нагузашт</th></tr></thead><tbody id="gmBody"></tbody></table></div>';
      main.appendChild(sec);
    }

    var f = document.getElementById('gmFilter');
    if (f && !f._gmBound) {
      f._gmBound = true;
      f.addEventListener('click', load);
    }
    document.querySelectorAll('.tab[data-tab="gmail"]').forEach(function (btn) {
      if (btn._gmBound) return;
      btn._gmBound = true;
      btn.addEventListener('click', function () {
        document.querySelectorAll('.tab').forEach(function (b) {
          b.classList.remove('active');
        });
        document.querySelectorAll('.tab-panel').forEach(function (p) {
          p.classList.add('hidden');
        });
        btn.classList.add('active');
        var sec = document.getElementById('tab-gmail');
        if (sec) sec.classList.remove('hidden');
        load();
      });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ensureTab);
  else ensureTab();
})();
