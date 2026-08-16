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
      admin = data.admin;
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
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
      btn.classList.add('active');
      const panel = document.getElementById('tab-' + btn.dataset.tab);
      if (panel) panel.classList.remove('hidden');
      if (btn.dataset.tab === 'monitor') loadMonitor();
      if (btn.dataset.tab === 'students') loadStudents();
      if (btn.dataset.tab === 'olympiads') loadOlympiads();
      if (btn.dataset.tab === 'results') loadOlympiadsForResults();
      if (btn.dataset.tab === 'admins') loadAdmins();
      if (btn.dataset.tab === 'schools') loadSchools();
    });
  });

  function statusBadge(status) {
    if (status === 'passed') return '<span class="badge">Гузашт</span>';
    if (status === 'failed') return '<span class="badge fail">Нагузашт</span>';
    return `<span class="badge off">${status || '—'}</span>`;
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&', '<': '<', '>': '>', '"': '"', "'": '&#39;',
    }[c]));
  }
  function escAttr(s) {
    return esc(s).replace(/`/g, '');
  }

  async function loadMonitor() {
    try {
      const data = await api('/api/admin/monitor');
      const s = data.stats || data || {};
      const _sg = document.getElementById('statsGrid');
      if (_sg) _sg.innerHTML = `
        <div class="stat"><b>${s.students || 0}</b><span>Хонандагон</span></div>
        <div class="stat"><b>${s.olympiads || 0}</b><span>Олимпиадаҳо</span></div>
        <div class="stat"><b>${s.activeOlympiads || 0}</b><span>Кушода ҳоло</span></div>
        <div class="stat"><b>${s.results || 0}</b><span>Натиҷаҳо</span></div>
        <div class="stat"><b>${s.passed || 0}</b><span>Гузаштанд</span></div>
        <div class="stat"><b>${s.failed || 0}</b><span>Нагузаштанд</span></div>
      `;
      const body = document.getElementById('recentResultsBody');
      const rows = data.recentResults || [];
      if (body) {
        body.innerHTML = rows.length ? rows.map((r) => `
          <tr>
            <td>${esc(r.studentName)}</td>
            <td>${esc(r.studentSchool || r.school)} / ${esc(r.studentClass || r.className)}</td>
            <td>${esc(r.olympiadTitle || '')}</td>
            <td><strong>${r.score ?? '—'}%</strong></td>
            <td>${statusBadge(r.status)}</td>
            <td>${esc((r.finishedAt || '').slice(0, 19).replace('T', ' '))}</td>
          </tr>
        `).join('') : '<tr><td colspan="6">Ҳанӯз натиҷа нест</td></tr>';
      }
    } catch (err) {
      if (String(err.message).includes('рад')) showLogin();
    }
  }

  document.getElementById('refreshLiveBtn')?.addEventListener('click', loadMonitor);

  // Student registration handled by js/admin-students-reg.js (9-field form).
  // Do NOT bind #fullName/#className/#school — those inputs no longer exist.

  document.getElementById('copyIdBtn')?.addEventListener('click', async () => {
    const id = document.getElementById('newIdValue')?.textContent || '';
    try {
      await navigator.clipboard.writeText(id);
      const btn = document.getElementById('copyIdBtn');
      if (btn) {
        btn.textContent = 'Нусха шуд';
        setTimeout(() => { btn.textContent = 'Нусха'; }, 1500);
      }
    } catch (_) {}
  });

  document.getElementById('exportStudentsBtn')?.addEventListener('click', async () => {
    try {
      const res = await fetch(API + '/api/admin/students/export', {
        credentials: 'include',
        headers: token ? { 'X-Admin-Token': token } : {},
      });
      if (!res.ok) throw new Error('Export хато');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'students.csv';
      a.click();
    } catch (err) {
      alert(err.message);
    }
  });

  async function loadStudents() {
    try {
      const data = await api('/api/admin/students');
      const body = document.getElementById('studentsBody');
      if (!body) return;
      const list = data.students || [];
      body.innerHTML = list.length ? list.map((s) => `
        <tr>
          <td><code>${esc(s.id)}</code></td>
          <td>${esc(s.fullName || '')}</td>
          <td>${esc(s.className || '')}</td>
          <td>${esc(s.school || '')}</td>
          <td>${esc(s.teacher || '')}</td>
          <td>${s.hasPhoto ? '✓' : '—'}</td>
          <td><button type="button" class="btn small danger" data-del-student="${esc(s.id)}">Нест</button></td>
        </tr>
      `).join('') : '<tr><td colspan="7">Хонанда нест</td></tr>';
      body.querySelectorAll('[data-del-student]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Хонанда нест карда шавад?')) return;
          await api('/api/admin/students/' + btn.dataset.delStudent, { method: 'DELETE' });
          loadStudents();
          loadMonitor();
        });
      });
    } catch (err) {
      if (String(err.message).includes('рад')) showLogin();
    }
  }

  const questionsList = document.getElementById('questionsList');
  let questionCount = 0;

  function addQuestion(prefill) {
    if (!questionsList) return;
    questionCount += 1;
    const n = questionCount;
    const wrap = document.createElement('div');
    wrap.className = 'question-card';
    wrap.dataset.q = n;
    wrap.innerHTML = `
      <div class="row-between">
        <strong>Савол ${n}</strong>
        <button type="button" class="btn small danger q-remove">×</button>
      </div>
      <input class="q-text" placeholder="Матни савол" value="${escAttr(prefill?.text || '')}" required />
      <div class="q-options"></div>
      <button type="button" class="btn small add-opt">+ Вариант</button>
    `;
    questionsList.appendChild(wrap);
    const optsBox = wrap.querySelector('.q-options');
    const options = prefill?.options || ['', '', '', ''];
    const answer = prefill?.answer ?? 0;
    function addOpt(val = '', checked = false) {
      const row = document.createElement('div');
      row.className = 'option-row';
      row.innerHTML = `
        <input type="radio" name="correct-${n}" ${checked ? 'checked' : ''} />
        <input type="text" class="opt-text" placeholder="Варианти ҷавоб" value="${escAttr(val)}" />
      `;
      optsBox.appendChild(row);
    }
    options.forEach((o, i) => addOpt(o, i === answer));
    wrap.querySelector('.add-opt').addEventListener('click', () => addOpt());
    wrap.querySelector('.q-remove').addEventListener('click', () => wrap.remove());
  }

  document.getElementById('addQuestionBtn')?.addEventListener('click', () => addQuestion());

  document.getElementById('olympiadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('olyFormMsg');
    msg?.classList.add('hidden');
    try {
      const cards = [...(questionsList?.querySelectorAll('.question-card') || [])];
      const questions = cards.map((card) => {
        const text = card.querySelector('.q-text')?.value.trim() || '';
        const opts = [...card.querySelectorAll('.opt-text')].map((i) => i.value.trim());
        const radios = [...card.querySelectorAll('input[type=radio]')];
        let answer = radios.findIndex((r) => r.checked);
        if (answer < 0) answer = 0;
        return { text, options: opts.filter(Boolean), answer };
      }).filter((q) => q.text && q.options.length >= 2);
      if (!questions.length) throw new Error('Ҳадди ақал 1 савол лозим аст');
      await api('/api/admin/olympiads', {
        method: 'POST',
        body: JSON.stringify({
          title: document.getElementById('olyTitle').value.trim(),
          type: document.getElementById('olyType').value,
          passScore: Number(document.getElementById('olyPass').value) || 70,
          startTime: document.getElementById('olyStart').value || null,
          endTime: document.getElementById('olyEnd').value || null,
          isActive: document.getElementById('olyActive').checked,
          questions,
        }),
      });
      if (msg) {
        msg.textContent = 'Сабт шуд';
        msg.classList.remove('hidden', 'error');
      }
      e.target.reset();
      if (questionsList) questionsList.innerHTML = '';
      questionCount = 0;
      loadOlympiads();
      loadMonitor();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message;
        msg.classList.remove('hidden');
        msg.classList.add('error');
      }
    }
  });

  async function loadOlympiads() {
    try {
      const data = await api('/api/admin/olympiads');
      const body = document.getElementById('olympiadsBody');
      if (!body) return;
      const list = data.olympiads || [];
      body.innerHTML = list.length ? list.map((o) => `
        <tr>
          <td>${esc(o.title)}</td>
          <td>${esc(o.type)}</td>
          <td>${o.questionCount ?? (o.questions || []).length}</td>
          <td>${o.passScore ?? 70}%</td>
          <td>${esc((o.startTime || '—').toString().slice(0, 16))} → ${esc((o.endTime || '—').toString().slice(0, 16))}</td>
          <td>${o.isActive ? '<span class="badge">Фаъол</span>' : '<span class="badge off">Хомӯш</span>'}</td>
          <td>
            <button type="button" class="btn small" data-toggle-oly="${esc(o.id)}">${o.isActive ? 'Хомӯш' : 'Фаъол'}</button>
            <button type="button" class="btn small danger" data-del-oly="${esc(o.id)}">Нест</button>
          </td>
        </tr>
      `).join('') : '<tr><td colspan="7">Олимпиада нест</td></tr>';
      body.querySelectorAll('[data-toggle-oly]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          await api('/api/admin/olympiads/' + btn.dataset.toggleOly, {
            method: 'PATCH',
            body: JSON.stringify({ isActive: btn.textContent.includes('Фаъол') }),
          });
          loadOlympiads();
          loadMonitor();
        });
      });
      body.querySelectorAll('[data-del-oly]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Нест карда шавад?')) return;
          await api('/api/admin/olympiads/' + btn.dataset.delOly, { method: 'DELETE' });
          loadOlympiads();
          loadMonitor();
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

  document.getElementById('resultOlympiadSelect')?.addEventListener('change', async (e) => {
    const id = e.target.value;
    if (!id) return;
    try {
      const data = await api('/api/admin/olympiads/' + id + '/results');
      const body = document.getElementById('resultsBody');
      if (!body) return;
      const rows = data.results || data || [];
      body.innerHTML = rows.length ? rows.map((r) => `
        <tr>
          <td>${esc(r.studentName)}</td>
          <td>${esc(r.school || r.studentSchool)}</td>
          <td>${esc(r.className || r.studentClass)}</td>
          <td>${r.score ?? '—'}%</td>
          <td>${statusBadge(r.status)}</td>
          <td>${esc((r.finishedAt || '').slice(0, 19).replace('T', ' '))}</td>
        </tr>
      `).join('') : '<tr><td colspan="6">Натиҷа нест</td></tr>';
    } catch (err) {
      alert(err.message);
    }
  });

  document.getElementById('adminForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('adminFormMsg');
    msg?.classList.add('hidden');
    try {
      await api('/api/admin/admins', {
        method: 'POST',
        body: JSON.stringify({
          name: document.getElementById('newAdminName').value.trim(),
          login: document.getElementById('newAdminLogin').value.trim(),
          password: document.getElementById('newAdminPassword').value,
        }),
      });
      if (msg) {
        msg.textContent = 'Админ илова шуд';
        msg.classList.remove('hidden', 'error');
      }
      e.target.reset();
      loadAdmins();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message;
        msg.classList.remove('hidden');
        msg.classList.add('error');
      }
    }
  });

  async function loadAdmins() {
    try {
      const data = await api('/api/admin/admins');
      const body = document.getElementById('adminsBody');
      if (!body) return;
      const list = data.admins || [];
      body.innerHTML = list.length ? list.map((a) => `
        <tr>
          <td>${esc(a.name)}</td>
          <td><code>${esc(a.login)}</code></td>
          <td>${esc(a.createdBy || '—')}</td>
          <td>${esc((a.createdAt || '').slice(0, 19).replace('T', ' '))}</td>
          <td>
            ${a.id === admin?.id
              ? '<span class="muted">шумо</span>'
              : `<button type="button" class="btn small danger" data-del-admin="${esc(a.id)}">Нест</button>`}
          </td>
        </tr>
      `).join('') : '<tr><td colspan="5">Админ нест</td></tr>';
      body.querySelectorAll('[data-del-admin]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Админ нест карда шавад?')) return;
          await api('/api/admin/admins/' + btn.dataset.delAdmin, { method: 'DELETE' });
          loadAdmins();
        });
      });
    } catch (err) {
      if (String(err.message).includes('рад')) showLogin();
    }
  }

  async function loadSchools() {
    try {
      const data = await api('/api/admin/schools');
      const body = document.getElementById('schoolsBody');
      if (!body) return;
      const list = data.schools || [];
      body.innerHTML = list.length ? list.map((s) => `
        <tr>
          <td>${esc(s.name)}</td>
          <td><button type="button" class="btn small danger" data-del-school="${esc(s.id)}">Нест</button></td>
        </tr>
      `).join('') : '<tr><td colspan="2">Мактаб нест</td></tr>';
      body.querySelectorAll('[data-del-school]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('Мактаб нест?')) return;
          await api('/api/admin/schools/' + btn.dataset.delSchool, { method: 'DELETE' });
          loadSchools();
        });
      });
    } catch (_) {}
  }

  document.getElementById('schoolForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('schoolFormMsg');
    try {
      await api('/api/admin/schools', {
        method: 'POST',
        body: JSON.stringify({ name: document.getElementById('schoolName').value.trim() }),
      });
      e.target.reset();
      loadSchools();
      if (msg) { msg.textContent = 'Илова шуд'; msg.classList.remove('hidden', 'error'); }
    } catch (err) {
      if (msg) { msg.textContent = err.message; msg.classList.remove('hidden'); msg.classList.add('error'); }
    }
  });

  (async () => {
    try {
      const res = await fetch(API + '/api/admin/me', { credentials: 'include' });
      const data = await res.json().catch(() => ({}));
      if (res.ok && (data.admin || data.authenticated)) {
        admin = data.admin || admin;
        if (admin) localStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
        showApp();
        return;
      }
    } catch (_) {}
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
