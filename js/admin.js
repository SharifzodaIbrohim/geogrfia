(() => {
  /* Admin panel — cookie session (credentials:include) + optional legacy token */
  const API = '';
  const TOKEN_KEY = 'geo_admin_token';
  const ADMIN_KEY = 'geo_admin_user';

  const loginView = document.getElementById('loginView');
  const appView = document.getElementById('appView');
  const loginForm = document.getElementById('adminLoginForm');
  const loginError = document.getElementById('loginError');
  const adminName = document.getElementById('adminName');
  const logoutBtn = document.getElementById('logoutBtn');

  let token = localStorage.getItem(TOKEN_KEY) || '';
  let admin = null;
  try { admin = JSON.parse(localStorage.getItem(ADMIN_KEY) || 'null'); } catch { admin = null; }

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['X-Admin-Token'] = token;
    const res = await fetch(API + path, { ...options, headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function showApp() {
    loginView.classList.add('hidden');
    appView.classList.remove('hidden');
    if (adminName) adminName.textContent = admin ? `· ${admin.name || admin.login}` : '';
    loadMonitor();
    loadStudents();
    loadOlympiads();
    loadAdmins();
    loadSchools();
  }

  function showLogin() {
    token = '';
    admin = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ADMIN_KEY);
    appView.classList.add('hidden');
    loginView.classList.remove('hidden');
    fetch(API + '/api/admin/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
  }

  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError?.classList.add('hidden');
    try {
      const data = await api('/api/admin/login', {
        method: 'POST',
        body: JSON.stringify({
          login: document.getElementById('adminLogin').value.trim(),
          password: document.getElementById('adminPassword').value,
        }),
      });
      token = data.token || '';
      admin = data.admin || null;
      if (token) localStorage.setItem(TOKEN_KEY, token);
      if (admin) localStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
      showApp();
    } catch (err) {
      if (loginError) {
        loginError.textContent = err.message;
        loginError.classList.remove('hidden');
      }
    }
  });

  logoutBtn?.addEventListener('click', showLogin);

  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
      const panel = document.getElementById('tab-' + btn.dataset.tab);
      if (panel) panel.classList.remove('hidden');
      if (btn.dataset.tab === 'olympiads') loadOlympiads();
      if (btn.dataset.tab === 'results') loadOlympiadsForResults();
      if (btn.dataset.tab === 'students') loadStudents();
      if (btn.dataset.tab === 'monitor') loadMonitor();
    });
  });

  async function loadMonitor() {
    try {
      const data = await api('/api/admin/monitor');
      const grid = document.getElementById('statsGrid');
      if (grid) {
        const s = data.stats || data;
        grid.innerHTML = `
          <div class="stat"><div class="num">${s.students ?? s.studentCount ?? '—'}</div><div class="lbl">Хонандагон</div></div>
          <div class="stat"><div class="num">${s.activeOlympiads ?? s.olympiads ?? '—'}</div><div class="lbl">Олимпиада</div></div>
          <div class="stat"><div class="num">${s.liveSessions ?? s.inProgress ?? '—'}</div><div class="lbl">Live</div></div>
          <div class="stat"><div class="num">${s.resultsToday ?? s.results ?? '—'}</div><div class="lbl">Натиҷа</div></div>
        `;
      }
      const liveBody = document.getElementById('liveSessionsBody');
      if (liveBody) {
        const rows = data.liveSessions || data.sessions || [];
        liveBody.innerHTML = rows.length
          ? rows.map((r) => `<tr><td>${esc(r.studentName || r.name || '—')}</td><td>${esc(r.studentId || r.code || '')}</td><td>${esc(r.olympiadTitle || r.title || '')}</td><td>${r.answered ?? '—'}</td><td>${esc(r.startedAt || '')}</td><td>${esc(r.expiresAt || '')}</td></tr>`).join('')
          : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
      }
      const recentBody = document.getElementById('recentResultsBody');
      if (recentBody) {
        const rows = data.recentResults || data.results || [];
        recentBody.innerHTML = rows.length
          ? rows.map((r) => `<tr><td>${esc(r.studentName || r.name || r.studentId || '—')}</td><td>${esc((r.school || '') + (r.className ? ' / ' + r.className : ''))}</td><td>${esc(r.olympiadTitle || r.title || '')}</td><td>${r.score ?? '—'}%</td><td>${esc(r.status || '')}</td><td>${esc(r.finishedAt || r.time || '')}</td></tr>`).join('')
          : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
      }
    } catch (err) {
      console.warn(err);
    }
  }

  document.getElementById('refreshLiveBtn')?.addEventListener('click', loadMonitor);
  document.getElementById('clearRecentBtn')?.addEventListener('click', async () => {
    try {
      await api('/api/admin/monitor/clear-recent', { method: 'POST' });
      loadMonitor();
    } catch (err) { alert(err.message); }
  });

  async function loadStudents() {
    try {
      const data = await api('/api/admin/students');
      const body = document.getElementById('studentsBody');
      if (!body) return;
      const list = data.students || [];
      body.innerHTML = list.length
        ? list.map((s) => {
            const id = s.id || s.studentCode || s.code || '';
            const name = s.fullName || [s.lastName, s.firstName].filter(Boolean).join(' ') || s.name || '—';
            return `<tr><td>${esc(id)}</td><td>${esc(name)}</td><td>${esc(s.className || '')}</td><td>${esc(s.school || s.schoolName || '')}</td><td>${esc(s.teacher || s.teacherName || '')}</td><td>${s.photoData || s.photo ? '✓' : '—'}</td><td><button type="button" class="btn small danger" data-del-student="${esc(id)}">Нест</button></td></tr>`;
          }).join('')
        : '<tr><td colspan="7" class="muted">Хонанда нест</td></tr>';
      body.querySelectorAll('[data-del-student]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Нест кардан?')) return;
          try {
            await api('/api/admin/students/' + btn.dataset.delStudent, { method: 'DELETE' });
            loadStudents();
          } catch (err) { alert(err.message); }
        });
      });
    } catch (err) {
      console.warn(err);
    }
  }

  /* Olympiad builder moved to js/admin-olympiad.js (multi-type).
     Do NOT collect single-only questions here — that broke short/match/text save. */
  document.getElementById('olympiadForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    if (typeof window.__geoSaveOlympiad === 'function') {
      window.__geoSaveOlympiad(e);
      return;
    }
    const msg = document.getElementById('olyFormMsg') || document.getElementById('olyMsg');
    if (msg) {
      msg.textContent = 'Скрипти олимпиада бор нашуд — Ctrl+F5';
      msg.classList.remove('hidden');
      msg.classList.add('error');
    }
  });
  document.getElementById('addQuestionBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    if (typeof window.__geoAddOlympiadQuestion === 'function') window.__geoAddOlympiadQuestion('single');
  });

  async function loadOlympiads() {
    // exposed for admin-olympiad.js
    try {
      const data = await api('/api/admin/olympiads');
      const body = document.getElementById('olympiadsBody');
      if (!body) return;
      const list = data.olympiads || [];
      body.innerHTML = list.length
        ? list.map((o) => `
        <tr>
          <td>${esc(o.title)}</td>
          <td>${esc(o.type || 'olympiad')}</td>
          <td>${o.passScore ?? 70}%</td>
          <td>${o.isActive ? 'Фаъол' : 'Хомӯш'}</td>
          <td>
            <button type="button" class="btn small" data-toggle-oly="${esc(o.id)}">${o.isActive ? 'Хомӯш' : 'Фаъол'}</button>
            <button type="button" class="btn small danger" data-del-oly="${esc(o.id)}">Нест</button>
          </td>
        </tr>`).join('')
        : '<tr><td colspan="5" class="muted">Холӣ</td></tr>';
      body.querySelectorAll('[data-toggle-oly]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          try {
            await api('/api/admin/olympiads/' + btn.dataset.toggleOly, {
              method: 'PATCH',
              body: JSON.stringify({ isActive: btn.textContent.includes('Фаъол') }),
            });
            loadOlympiads();
          } catch (err) { alert(err.message); }
        });
      });
      body.querySelectorAll('[data-del-oly]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Нест?')) return;
          try {
            await api('/api/admin/olympiads/' + btn.dataset.delOly, { method: 'DELETE' });
            loadOlympiads();
          } catch (err) { alert(err.message); }
        });
      });
      const sel = document.getElementById('resultOlympiadSelect');
      if (sel) {
        const cur = sel.value;
        sel.innerHTML = '<option value="">— интихоб —</option>' +
          list.map((o) => `<option value="${esc(o.id)}">${esc(o.title)}</option>`).join('');
        if (cur) sel.value = cur;
      }
    } catch (err) {
      if (String(err.message).includes('рад')) showLogin();
    }
  }

  function loadOlympiadsForResults() {
    loadOlympiads();
  }
  window.loadOlympiads = loadOlympiads;
  window.loadMonitor = typeof loadMonitor === 'function' ? loadMonitor : window.loadMonitor;

  document.getElementById('resultOlympiadSelect')?.addEventListener('change', async (e) => {
    const id = e.target.value;
    if (!id) return;
    try {
      const data = await api('/api/admin/olympiads/' + id + '/results');
      const body = document.getElementById('resultsBody');
      if (!body) return;
      const rows = data.results || data.items || [];
      body.innerHTML = rows.length
        ? rows.map((r) => `<tr><td>${esc(r.studentName || r.name || '—')}</td><td>${esc(r.school || '')}</td><td>${esc(r.className || '')}</td><td>${r.score ?? '—'}%</td><td>${esc(r.status || '')}</td><td>${esc(r.finishedAt || '')}</td></tr>`).join('')
        : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
    } catch (err) { console.warn(err); }
  });
  document.getElementById('loadResultsBtn')?.addEventListener('click', () => {
    const sel = document.getElementById('resultOlympiadSelect');
    if (sel) sel.dispatchEvent(new Event('change'));
  });

  async function loadAdmins() {
    try {
      const data = await api('/api/admin/admins');
      const body = document.getElementById('adminsBody');
      if (!body) return;
      const list = data.admins || [];
      body.innerHTML = list.map((a) => `
        <tr><td>${esc(a.login)}</td><td>${esc(a.name || '')}</td><td>${esc(a.role || '')}</td>
        <td><button type="button" class="btn small danger" data-del-admin="${esc(a.id || a.login)}">Нест</button></td></tr>`).join('');
      body.querySelectorAll('[data-del-admin]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Нест?')) return;
          try {
            await api('/api/admin/admins/' + btn.dataset.delAdmin, { method: 'DELETE' });
            loadAdmins();
          } catch (err) { alert(err.message); }
        });
      });
    } catch (err) { console.warn(err); }
  }

  document.getElementById('adminForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/admin/admins', {
        method: 'POST',
        body: JSON.stringify({
          login: document.getElementById('newAdminLogin').value.trim(),
          name: document.getElementById('newAdminName').value.trim(),
          password: document.getElementById('newAdminPassword').value,
          role: document.getElementById('newAdminRole').value,
        }),
      });
      e.target.reset();
      loadAdmins();
    } catch (err) { alert(err.message); }
  });

  async function loadSchools() {
    try {
      const data = await api('/api/admin/schools');
      const body = document.getElementById('schoolsBody');
      if (!body) return;
      const list = data.schools || [];
      body.innerHTML = list.map((s) => `
        <tr><td>${esc(s.name)}</td><td>${esc(s.location || '')}</td>
        <td><button type="button" class="btn small danger" data-del-school="${esc(s.id)}">Нест</button></td></tr>`).join('');
      body.querySelectorAll('[data-del-school]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          try {
            await api('/api/admin/schools/' + btn.dataset.delSchool, { method: 'DELETE' });
            loadSchools();
          } catch (err) { alert(err.message); }
        });
      });
    } catch (err) { console.warn(err); }
  }

  document.getElementById('schoolForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/admin/schools', {
        method: 'POST',
        body: JSON.stringify({
          name: document.getElementById('schoolName').value.trim(),
          location: document.getElementById('schoolLocation').value.trim(),
        }),
      });
      e.target.reset();
      loadSchools();
    } catch (err) { alert(err.message); }
  });

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function escAttr(s) { return esc(s); }

  (async () => {
    if (token && admin) {
      try {
        await api('/api/admin/me');
        showApp();
        return;
      } catch (_) {}
    }
    showLogin();
  })();
})();
