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
    const res = await fetch(API + path, { ...options, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function showApp() {
    loginView.classList.add('hidden');
    appView.classList.remove('hidden');
    adminName.textContent = admin ? `· ${admin.name || admin.login}` : '';
    loadMonitor();
    loadStudents();
    loadOlympiads();
  }

  function showLogin() {
    token = '';
    admin = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ADMIN_KEY);
    appView.classList.add('hidden');
    loginView.classList.remove('hidden');
  }

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.classList.add('hidden');
    try {
      const data = await api('/api/admin/login', {
        method: 'POST',
        body: JSON.stringify({
          login: document.getElementById('adminLogin').value.trim(),
          password: document.getElementById('adminPassword').value,
        }),
      });
      token = data.token;
      admin = data.admin;
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
      showApp();
    } catch (err) {
      loginError.textContent = err.message;
      loginError.classList.remove('hidden');
    }
  });

  logoutBtn.addEventListener('click', showLogin);

  // Tabs
  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
      if (btn.dataset.tab === 'monitor') loadMonitor();
      if (btn.dataset.tab === 'students') loadStudents();
      if (btn.dataset.tab === 'olympiads') loadOlympiads();
      if (btn.dataset.tab === 'results') loadOlympiadsForResults();
    });
  });

  function statusBadge(status) {
    if (status === 'passed') return '<span class="badge">Гузашт</span>';
    if (status === 'failed') return '<span class="badge fail">Нагузашт</span>';
    return `<span class="badge off">${status || '—'}</span>`;
  }

  async function loadMonitor() {
    try {
      const data = await api('/api/admin/monitor');
      const s = data.stats || {};
      document.getElementById('statsGrid').innerHTML = `
        <div class="stat"><b>${s.students || 0}</b><span>Хонандагон</span></div>
        <div class="stat"><b>${s.olympiads || 0}</b><span>Олимпиадаҳо</span></div>
        <div class="stat"><b>${s.activeOlympiads || 0}</b><span>Фаъол</span></div>
        <div class="stat"><b>${s.results || 0}</b><span>Натиҷаҳо</span></div>
        <div class="stat"><b>${s.passed || 0}</b><span>Гузаштанд</span></div>
        <div class="stat"><b>${s.failed || 0}</b><span>Нагузаштанд</span></div>
      `;
      const body = document.getElementById('recentResultsBody');
      const rows = data.recentResults || [];
      body.innerHTML = rows.length ? rows.map((r) => `
        <tr>
          <td>${esc(r.studentName)}</td>
          <td>${esc(r.studentSchool)} / ${esc(r.studentClass)}</td>
          <td>${esc(r.olympiadTitle)}</td>
          <td><strong>${r.score}%</strong></td>
          <td>${statusBadge(r.status)}</td>
          <td>${esc((r.finishedAt || '').slice(0, 19).replace('T', ' '))}</td>
        </tr>
      `).join('') : '<tr><td colspan="6">Ҳанӯз натиҷа нест</td></tr>';
    } catch (err) {
      if (String(err.message).includes('рад')) showLogin();
    }
  }

  // Students
  const studentForm = document.getElementById('studentForm');
  studentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('studentFormMsg');
    msg.classList.add('hidden');
    try {
      const data = await api('/api/admin/students', {
        method: 'POST',
        body: JSON.stringify({
          fullName: document.getElementById('fullName').value.trim(),
          className: document.getElementById('className').value.trim(),
          school: document.getElementById('school').value.trim(),
        }),
      });
      studentForm.reset();
      const s = data.student;
      document.getElementById('newIdBox').classList.remove('hidden');
      document.getElementById('newIdName').textContent = s.fullName;
      document.getElementById('newIdValue').textContent = s.id;
      loadStudents();
      loadMonitor();
    } catch (err) {
      msg.textContent = err.message;
      msg.classList.remove('hidden');
      msg.classList.add('error');
    }
  });

  document.getElementById('copyIdBtn').addEventListener('click', async () => {
    const id = document.getElementById('newIdValue').textContent;
    try {
      await navigator.clipboard.writeText(id);
      document.getElementById('copyIdBtn').textContent = 'Нусха шуд';
      setTimeout(() => { document.getElementById('copyIdBtn').textContent = 'Нусха'; }, 1500);
    } catch {}
  });

  async function loadStudents() {
    try {
      const data = await api('/api/admin/students');
      const body = document.getElementById('studentsBody');
      const list = data.students || [];
      body.innerHTML = list.length ? list.map((s) => `
        <tr>
          <td><code>${esc(s.id)}</code></td>
          <td>${esc(s.fullName)}</td>
          <td>${esc(s.className)}</td>
          <td>${esc(s.school)}</td>
          <td><button type="button" class="btn small danger" data-del-student="${esc(s.id)}">Нест</button></td>
        </tr>
      `).join('') : '<tr><td colspan="5">Хонанда нест</td></tr>';

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

  // Olympiads — question builder
  const questionsList = document.getElementById('questionsList');
  let questionCount = 0;

  function addQuestion(prefill) {
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

    wrap.querySelector('.add-opt').addEventListener('click', () => addOpt(''));
    wrap.querySelector('.q-remove').addEventListener('click', () => wrap.remove());
  }

  document.getElementById('addQuestionBtn').addEventListener('click', () => addQuestion());
  addQuestion();

  document.getElementById('olympiadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('olyFormMsg');
    msg.classList.add('hidden');

    const questions = [];
    document.querySelectorAll('.question-card').forEach((card) => {
      const text = card.querySelector('.q-text').value.trim();
      const optionInputs = [...card.querySelectorAll('.opt-text')];
      const radios = [...card.querySelectorAll('input[type=radio]')];
      const options = optionInputs.map((i) => i.value.trim()).filter(Boolean);
      let answer = 0;
      radios.forEach((r, idx) => { if (r.checked) answer = idx; });
      // map answer index to filtered options index approximately by original order
      const allVals = optionInputs.map((i) => i.value.trim());
      const selectedRaw = allVals.findIndex((_, i) => radios[i]?.checked);
      const selectedVal = selectedRaw >= 0 ? allVals[selectedRaw] : allVals[0];
      answer = Math.max(0, options.indexOf(selectedVal));
      if (text && options.length >= 2) {
        questions.push({ text, options, answer });
      }
    });

    try {
      await api('/api/admin/olympiads', {
        method: 'POST',
        body: JSON.stringify({
          title: document.getElementById('olyTitle').value.trim(),
          type: document.getElementById('olyType').value,
          passScore: Number(document.getElementById('olyPass').value) || 70,
          isActive: document.getElementById('olyActive').checked,
          questions,
        }),
      });
      msg.textContent = 'Сабт шуд';
      msg.classList.remove('hidden', 'error');
      document.getElementById('olympiadForm').reset();
      questionsList.innerHTML = '';
      questionCount = 0;
      addQuestion();
      loadOlympiads();
      loadMonitor();
    } catch (err) {
      msg.textContent = err.message;
      msg.classList.remove('hidden');
      msg.classList.add('error');
    }
  });

  async function loadOlympiads() {
    try {
      const data = await api('/api/admin/olympiads');
      const body = document.getElementById('olympiadsBody');
      const list = data.olympiads || [];
      body.innerHTML = list.length ? list.map((o) => `
        <tr>
          <td>${esc(o.title)}</td>
          <td>${o.type === 'quiz' ? 'Викторина' : 'Олимпиада'}</td>
          <td>${o.questionCount || 0}</td>
          <td>${o.passScore}%</td>
          <td>${o.isActive ? '<span class="badge">Фаъол</span>' : '<span class="badge off">Хомӯш</span>'}</td>
          <td>
            <button type="button" class="btn small" data-toggle-oly="${esc(o.id)}" data-active="${o.isActive ? '1' : '0'}">
              ${o.isActive ? 'Хомӯш' : 'Фаъол'}
            </button>
            <button type="button" class="btn small danger" data-del-oly="${esc(o.id)}">Нест</button>
          </td>
        </tr>
      `).join('') : '<tr><td colspan="6">Ҳанӯз нест</td></tr>';

      body.querySelectorAll('[data-toggle-oly]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const active = btn.dataset.active !== '1';
          await api('/api/admin/olympiads/' + btn.dataset.toggleOly, {
            method: 'PATCH',
            body: JSON.stringify({ isActive: active }),
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

      // fill results select
      const sel = document.getElementById('resultOlympiadSelect');
      const current = sel.value;
      sel.innerHTML = '<option value="">— интихоб —</option>' +
        list.map((o) => `<option value="${esc(o.id)}">${esc(o.title)}</option>`).join('');
      if (current) sel.value = current;
    } catch (err) {
      if (String(err.message).includes('рад')) showLogin();
    }
  }

  async function loadOlympiadsForResults() {
    await loadOlympiads();
  }

  document.getElementById('resultOlympiadSelect').addEventListener('change', async (e) => {
    const id = e.target.value;
    const body = document.getElementById('resultsBody');
    if (!id) {
      body.innerHTML = '';
      return;
    }
    try {
      const data = await api('/api/admin/olympiads/' + id + '/results');
      const rows = data.results || [];
      body.innerHTML = rows.length ? rows.map((r) => `
        <tr>
          <td>${esc(r.studentName)}</td>
          <td>${esc(r.studentClass)}</td>
          <td>${esc(r.studentSchool)}</td>
          <td><strong>${r.score}%</strong></td>
          <td>${r.correct}/${r.total}</td>
          <td>${statusBadge(r.status)}</td>
          <td>${esc((r.finishedAt || '').slice(0, 19).replace('T', ' '))}</td>
        </tr>
      `).join('') : '<tr><td colspan="7">Натиҷа нест</td></tr>';
    } catch (err) {
      body.innerHTML = `<tr><td colspan="7">${esc(err.message)}</td></tr>`;
    }
  });

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }
  function escAttr(s) {
    return esc(s).replace(/`/g, '');
  }

  // boot
  if (token && admin) {
    api('/api/admin/me').then(showApp).catch(showLogin);
  }
})();
