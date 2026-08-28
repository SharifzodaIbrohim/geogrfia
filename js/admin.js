(() => {
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
    try { if (window.__adminRbacApply) window.__adminRbacApply(); } catch (_) {}
    if (adminName) adminName.textContent = admin ? `· ${admin.name || admin.login}` : '';
    loadMonitor(); loadStudents(); loadOlympiads(); loadAdmins(); loadSchools();
  }
  function showLogin() {
    token = ''; admin = null;
    localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(ADMIN_KEY);
    appView.classList.add('hidden'); loginView.classList.remove('hidden');
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
      if (loginError) { loginError.textContent = err.message; loginError.classList.remove('hidden'); }
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
      if (btn.dataset.tab === 'results') loadOlympiads();
      if (btn.dataset.tab === 'students') loadStudents();
      if (btn.dataset.tab === 'monitor') loadMonitor();
    });
  });

  function statusLabel(st) {
    const s = String(st || '').toLowerCase();
    if (s === 'passed' || s === 'pass' || s === 'гузашт') return 'Гузашт';
    if (s === 'failed' || s === 'fail' || s === 'нагузашт') return 'Нагузашт';
    if (s === 'in_progress' || s === 'in-progress') return 'Дар ҷараён';
    if (s === 'timeout' || s === 'expired') return 'Вақт тамом';
    if (s === 'submitted') return 'Супорида шуд';
    return st || '—';
  }
  function displayName(r) {
    const n = r.studentName || r.name || r.fullName || '';
    if (n && !/^\d{10,}$/.test(String(n).trim())) return n;
    if (r.lastName || r.firstName) return [r.lastName, r.firstName].filter(Boolean).join(' ');
    return n || '—';
  }
  /** Display score as points + percent (not only %). Does not change scoring. */
  function formatScoreCell(r) {
    const earned = r.earned != null ? r.earned : (r.pointsEarned != null ? r.pointsEarned : r.points);
    const totalMax = r.totalMax != null ? r.totalMax : (r.maxScore != null ? r.maxScore : r.totalPoints);
    const correct = r.correct;
    const total = r.total;
    let pct = null;
    if (r.score != null && r.score !== '') {
      pct = String(r.score).includes('%') ? String(r.score) : (r.score + '%');
    }
    let points = '';
    if (earned != null && totalMax != null) {
      points = earned + '/' + totalMax + ' хол';
    } else if (correct != null && total != null) {
      points = correct + '/' + total;
    }
    if (points && pct) return points + ' · ' + pct;
    if (points) return points;
    if (pct) return pct;
    return '—';
  }

  async function loadMonitor() {
    try {
      const data = await api('/api/admin/monitor');
      const grid = document.getElementById('statsGrid');
      if (grid) {
        const s = data.stats || data;
        const liveN = (data.liveSessions || data.sessions || []).length || s.liveSessions || s.inProgress || 0;
        grid.innerHTML = `
          <div class="stat"><div class="num">${s.students ?? s.studentCount ?? '—'}</div><div class="lbl">Хонандагон</div></div>
          <div class="stat"><div class="num">${s.activeOlympiads ?? s.olympiads ?? '—'}</div><div class="lbl">Олимпиада</div></div>
          <div class="stat"><div class="num">${liveN}</div><div class="lbl">Live</div></div>
          <div class="stat"><div class="num">${s.resultsToday ?? s.results ?? '—'}</div><div class="lbl">Натиҷа</div></div>
          <div class="stat"><div class="num">${s.passed ?? '—'}</div><div class="lbl">Гузашт</div></div>
          <div class="stat"><div class="num">${s.failed ?? '—'}</div><div class="lbl">Нагузашт</div></div>`;
      }
      const liveBody = document.getElementById('liveSessionsBody');
      if (liveBody) {
        const rows = data.liveSessions || data.sessions || [];
        liveBody.innerHTML = rows.length
          ? rows.map((r) => `<tr>
              <td>${esc(displayName(r))}</td>
              <td><code>${esc(r.studentId || r.code || '')}</code></td>
              <td>${esc(r.olympiadTitle || r.title || '')}</td>
              <td>${r.answered ?? '—'}</td>
              <td>${esc(r.startedAt || '')}</td>
              <td>${esc(r.expiresAt || r.endsAt || '')}</td>
            </tr>`).join('')
          : '<tr><td colspan="6" class="muted">Сессияи зинда нест</td></tr>';
      }
      const recentBody = document.getElementById('recentResultsBody');
      if (recentBody) {
        const rows = data.recentResults || data.results || [];
        recentBody.innerHTML = rows.length
          ? rows.map((r) => {
              const st = statusLabel(r.status);
              const stClass = (String(r.status||'').toLowerCase()==='passed') ? 'ok' : ((String(r.status||'').toLowerCase()==='failed') ? 'error' : '');
              const score = formatScoreCell(r);
              const school = [r.school, r.className].filter(Boolean).join(' / ');
              return `<tr>
                <td>${esc(displayName(r))}</td>
                <td>${esc(school || '—')}</td>
                <td>${esc(r.olympiadTitle || r.title || '')}</td>
                <td>${esc(score)}</td>
                <td class="${stClass}">${esc(st)}</td>
                <td>${esc(r.finishedAt || r.time || r.submittedAt || '')}</td>
              </tr>`;
            }).join('')
          : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
      }
    } catch (err) {
      console.warn('loadMonitor', err);
      const grid = document.getElementById('statsGrid');
      if (grid) grid.innerHTML = `<div class="muted">Хато: ${esc(err.message || err)}</div>`;
    }
  }

  window.loadMonitor = loadMonitor;
  document.getElementById('refreshLiveBtn')?.addEventListener('click', loadMonitor);
  async function clearRecentHandler() {
    if (!confirm('Натиҷаҳои охирин (то 30) аз база пок шаванд? Ин бебозгашт аст.')) return;
    try {
      try { await api('/api/admin/monitor/clear-recent', { method: 'POST', body: '{}' }); }
      catch (_) { await api('/api/admin/results/clear-recent', { method: 'POST', body: '{}' }); }
      loadMonitor();
    } catch (err) { alert(err.message || 'Пок карда нашуд'); }
  }
  ['clearRecentBtn', 'btnClearRecent', 'clearRecentResultsBtn'].forEach((id) => {
    const el = document.getElementById(id);
    if (el && !el._adminJsClear) {
      el._adminJsClear = true;
      el.addEventListener('click', (ev) => { ev.preventDefault(); clearRecentHandler(); });
    }
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
        btn.addEventListener('click', async (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          const id = btn.getAttribute('data-del-student') || btn.dataset.delStudent || '';
          if (!id) return;
          if (!confirm('Хонандаро нест кунем?\nID: ' + id)) return;
          try {
            await api('/api/admin/students/' + encodeURIComponent(id), { method: 'DELETE' });
            loadStudents();
            loadMonitor();
          } catch (err) {
            try {
              await api('/api/admin/students/delete', { method: 'POST', body: JSON.stringify({ id: id, studentId: id }) });
              loadStudents();
              loadMonitor();
            } catch (e2) {
              alert('Нест нашуд: ' + (err.message || err));
            }
          }
        });
      });
    } catch (err) { console.warn(err); }
  }
  document.getElementById('olympiadForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    if (typeof window.__geoSaveOlympiad === 'function') { window.__geoSaveOlympiad(e); return; }
    const msg = document.getElementById('olyFormMsg') || document.getElementById('olyMsg');
    if (msg) { msg.textContent = 'Скрипти олимпиада бор нашуд — Ctrl+F5'; msg.classList.remove('hidden'); msg.classList.add('error'); }
  });
  async function loadOlympiads() {
    try {
      const data = await api('/api/admin/olympiads');
      const body = document.getElementById('olympiadsBody');
      if (!body) return;
      const list = data.olympiads || [];
      body.innerHTML = list.length
        ? list.map((o) => {
            const dm = o.durationMin != null ? o.durationMin
              : (o.durationSec != null ? (o.durationSec === 0 ? 0 : Math.round(o.durationSec / 60)) : null);
            const durTxt = dm === 0 ? 'Бе вақт' : (dm != null ? (dm + ' дақ') : '—');
            return `<tr>
          <td>${esc(o.title)}</td><td>${esc(o.type || 'olympiad')}</td><td>${o.passScore ?? 70}%</td>
          <td>${esc(durTxt)}</td>
          <td>${o.isActive ? 'Фаъол' : 'Хомӯш'}</td>
          <td>
            <button type="button" class="btn small" data-toggle-oly="${esc(o.id)}">${o.isActive ? 'Хомӯш' : 'Фаъол'}</button>
            <button type="button" class="btn small danger" data-del-oly="${esc(o.id)}">Нест</button>
          </td></tr>`;
          }).join('')
        : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
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
  window.loadOlympiads = loadOlympiads;
  window.loadMonitor = loadMonitor;
  document.getElementById('resultOlympiadSelect')?.addEventListener('change', async (e) => {
    const id = e.target.value;
    if (!id) return;
    try {
      const data = await api('/api/admin/olympiads/' + id + '/results');
      const body = document.getElementById('resultsBody');
      if (!body) return;
      const rows = data.results || data.items || [];
      body.innerHTML = rows.length
        ? rows.map((r) => `<tr><td>${esc(displayName(r))}</td><td>${esc(r.school || '')}</td><td>${esc(r.className || '')}</td><td>${esc(formatScoreCell(r))}</td><td>${esc(statusLabel(r.status))}</td><td>${esc(r.finishedAt || '')}</td></tr>`).join('')
        : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
    } catch (err) { console.warn(err); }
  });
  document.getElementById('loadResultsBtn')?.addEventListener('click', () => {
    document.getElementById('resultOlympiadSelect')?.dispatchEvent(new Event('change'));
  });
  async function loadAdmins() {
    try {
      const data = await api('/api/admin/admins');
      const body = document.getElementById('adminsBody');
      if (!body) return;
      const list = data.admins || [];
      body.innerHTML = list.map((a) => {
        const role = a.role || a.Role || '—';
        return `<tr><td>${esc(a.login)}</td><td>${esc(a.name || '')}</td><td>${esc(role)}</td>
        <td><button type="button" class="btn small danger" data-del-admin="${esc(a.id || a.login)}">Нест</button></td></tr>`;
      }).join('');
      body.querySelectorAll('[data-del-admin]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Нест кардани ин админ?')) return;
          try {
            await api('/api/admin/admins/' + encodeURIComponent(btn.dataset.delAdmin), { method: 'DELETE' });
            loadAdmins();
          } catch (err) {
            alert(err.message || 'Нест карда нашуд (ҳуқуқ / охирин админ / худ)');
          }
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
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      if (c === '&') return '&' + 'amp;';
      if (c === '<') return '&' + 'lt;';
      if (c === '>') return '&' + 'gt;';
      if (c === '"') return '&' + 'quot;';
      return '&#39;';
    });
  }
  (async () => {
    if (token && admin) {
      try { await api('/api/admin/me'); showApp(); return; } catch (_) {}
    }
    try {
      const me = await api('/api/admin/me');
      if (me && (me.admin || me.login || me.ok)) {
        admin = me.admin || me;
        if (admin) localStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
        showApp(); return;
      }
    } catch (_) {}
    showLogin();
  })();
})();
