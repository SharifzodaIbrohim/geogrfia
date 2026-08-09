(() => {
  const API = '';
  const STUDENT_KEY = 'geo_student';

  const loginView = document.getElementById('loginView');
  const appView = document.getElementById('appView');
  const loginForm = document.getElementById('studentLoginForm');
  const loginError = document.getElementById('loginError');
  const logoutBtn = document.getElementById('logoutBtn');

  const listView = document.getElementById('listView');
  const examView = document.getElementById('examView');
  const resultView = document.getElementById('resultView');

  let student = null;
  try { student = JSON.parse(localStorage.getItem(STUDENT_KEY) || 'null'); } catch { student = null; }

  let currentOlympiad = null;
  let examSession = null;
  const answers = new Map();
  let examTimerId = null;
  let autosaveTimer = null;

  let FP = localStorage.getItem('geo_fp');
  if (!FP) {
    FP = Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('geo_fp', FP);
  }

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (options.headers) Object.assign(headers, options.headers);
    const res = await fetch(API + path, { ...options, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function showApp() {
    loginView.classList.add('hidden');
    appView.classList.remove('hidden');
    document.getElementById('studentName').textContent = student.fullName;
    document.getElementById('studentMeta').textContent =
      `· ${student.className} · ${student.school} · ID: ${student.id}`;
    showList();
    loadActive();
  }

  function showLogin() {
    student = null;
    localStorage.removeItem(STUDENT_KEY);
    appView.classList.add('hidden');
    loginView.classList.remove('hidden');
  }

  function showList() {
    stopExamTimers();
    listView.classList.remove('hidden');
    examView.classList.add('hidden');
    resultView.classList.add('hidden');
  }

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.classList.add('hidden');
    try {
      const data = await api('/api/student/login', {
        method: 'POST',
        body: JSON.stringify({ id: document.getElementById('studentIdInput').value.trim() }),
      });
      student = data.student;
      localStorage.setItem(STUDENT_KEY, JSON.stringify(student));
      showApp();
    } catch (err) {
      loginError.textContent = err.message;
      loginError.classList.remove('hidden');
    }
  });

  logoutBtn.addEventListener('click', showLogin);
  document.getElementById('backToListBtn').addEventListener('click', () => {
    showList();
    loadActive();
  });

  async function loadActive() {
    const box = document.getElementById('olympiadList');
    const empty = document.getElementById('emptyOly');
    try {
      const data = await api('/api/olympiads/active');
      const list = data.olympiads || [];
      if (!list.length) {
        box.innerHTML = '';
        empty.classList.remove('hidden');
        return;
      }
      empty.classList.add('hidden');
      box.innerHTML = list.map((o) => `
        <div class="oly-card">
          <h3>${esc(o.title)}</h3>
          <p class="muted">${o.type === 'quiz' ? 'Викторина' : 'Олимпиада'} · ${o.questionCount} савол · ҳад ${o.passScore}%</p>
          <button type="button" class="btn primary" data-start="${esc(o.id)}">Оғоз</button>
        </div>
      `).join('');

      box.querySelectorAll('[data-start]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const oly = list.find((x) => x.id === btn.dataset.start);
          if (oly) await startExam(oly);
        });
      });
    } catch (err) {
      box.innerHTML = `<p class="error">${esc(err.message)}</p>`;
    }
  }

  function stopExamTimers() {
    if (examTimerId) { clearInterval(examTimerId); examTimerId = null; }
    if (autosaveTimer) { clearInterval(autosaveTimer); autosaveTimer = null; }
  }

  function tickExamTimer() {
    const el = document.getElementById('examTimer');
    if (!el) return;
    if (!examSession || !examSession.endsAt) {
      el.textContent = '—';
      return;
    }
    const ms = new Date(examSession.endsAt) - Date.now();
    if (ms <= 0) {
      el.textContent = '00:00';
      stopExamTimers();
      submitExam(true);
      return;
    }
    const sec = Math.ceil(ms / 1000);
    const m = String(Math.floor(sec / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    el.textContent = m + ':' + s;
  }

  async function doAutosave() {
    if (!examSession || !currentOlympiad) return;
    const payload = {};
    (examSession.questions || []).forEach((q) => {
      if (answers.has(q.id)) payload[String(q.originalIndex)] = answers.get(q.id);
    });
    try {
      await api('/api/olympiads/' + currentOlympiad.id + '/autosave', {
        method: 'POST',
        headers: { 'X-Client-Fingerprint': FP },
        body: JSON.stringify({
          sessionId: examSession.sessionId,
          sessionToken: examSession.sessionToken,
          answers: payload,
        }),
      });
    } catch (e) { /* silent */ }
  }

  async function startExam(oly) {
    try {
      const data = await api('/api/olympiads/' + oly.id + '/start', {
        method: 'POST',
        headers: { 'X-Client-Fingerprint': FP },
        body: JSON.stringify({ studentId: student.id }),
      });
      examSession = data;
      currentOlympiad = {
        ...oly,
        id: data.olympiadId || oly.id,
        questions: data.questions || [],
        title: data.title || oly.title,
        passScore: data.passScore,
      };
      answers.clear();
      (data.questions || []).forEach((q) => {
        if (q.selected != null && q.selected !== undefined) answers.set(q.id, q.selected);
      });
      listView.classList.add('hidden');
      resultView.classList.add('hidden');
      examView.classList.remove('hidden');
      document.getElementById('examTitle').textContent = currentOlympiad.title;
      const msg = document.getElementById('examMsg');
      if (msg) msg.classList.add('hidden');
      renderExamQuestions();
      stopExamTimers();
      tickExamTimer();
      examTimerId = setInterval(tickExamTimer, 500);
      autosaveTimer = setInterval(doAutosave, 15000);
    } catch (err) {
      alert(err.message || 'Хато');
    }
  }

  function renderExamQuestions() {
    const box = document.getElementById('examQuestions');
    const qs = currentOlympiad.questions || [];
    box.innerHTML = qs.map((q, idx) => `
      <div class="exam-q" data-qid="${esc(String(q.id))}">
        <h4>${idx + 1}. ${esc(q.text)}</h4>
        <div class="exam-opts">
          ${(q.options || []).map((opt, oi) => `
            <label class="exam-opt">
              <input type="radio" name="q-${esc(String(q.id))}" value="${oi}" ${answers.get(q.id) === oi ? 'checked' : ''} />
              <span>${esc(opt)}</span>
            </label>
          `).join('')}
        </div>
      </div>
    `).join('');
    box.querySelectorAll('input[type=radio]').forEach((inp) => {
      inp.addEventListener('change', () => {
        const qid = inp.name.replace(/^q-/, '');
        const num = Number(qid);
        const key = Number.isNaN(num) ? qid : num;
        answers.set(key, Number(inp.value));
        if (key !== qid) answers.set(qid, Number(inp.value));
        updateProgress();
        doAutosave();
      });
    });
    updateProgress();
  }

  function updateProgress() {
    const total = (currentOlympiad.questions || []).length;
    const el = document.getElementById('examProgress');
    if (el) el.textContent = `${answers.size}/${total}`;
  }

  async function submitExam(auto) {
    if (!examSession || !currentOlympiad) return;
    stopExamTimers();
    const payload = {};
    (examSession.questions || []).forEach((q) => {
      let sel = answers.has(q.id) ? answers.get(q.id) : null;
      if (sel == null && answers.has(String(q.id))) sel = answers.get(String(q.id));
      if (sel != null) payload[String(q.originalIndex)] = sel;
    });
    try {
      const data = await api('/api/olympiads/' + currentOlympiad.id + '/exam-submit', {
        method: 'POST',
        headers: { 'X-Client-Fingerprint': FP },
        body: JSON.stringify({
          sessionId: examSession.sessionId,
          sessionToken: examSession.sessionToken,
          answers: payload,
        }),
      });
      const r = data.result || {};
      examView.classList.add('hidden');
      resultView.classList.remove('hidden');
      document.getElementById('resultScore').textContent = (r.score ?? '—') + '%';
      document.getElementById('resultDetail').textContent =
        `Дуруст: ${r.correct} аз ${r.total} · ҳад: ${r.passScore}%` +
        (r.timedOut ? ' · вақт тамом' : '') +
        (auto ? ' · худкор' : '');
      const st = document.getElementById('resultStatus');
      if (st) {
        st.textContent = r.status === 'passed' ? 'Гузашт' : 'Нагузашт';
        st.className = 'badge' + (r.status === 'passed' ? '' : ' fail');
      }
      examSession = null;
    } catch (err) {
      const msg = document.getElementById('examMsg');
      if (msg) {
        msg.textContent = err.message;
        msg.classList.remove('hidden');
        msg.classList.add('error');
      } else {
        alert(err.message);
      }
    }
  }

  document.getElementById('submitExamBtn').addEventListener('click', async () => {
    if (!examSession || !currentOlympiad) return;
    const total = (currentOlympiad.questions || []).length;
    if (answers.size < total) {
      if (!confirm('Баъзе саволҳо ҷавоб надоранд. Ба ҳар ҳол супоред?')) return;
    }
    await submitExam(false);
  });

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  if (student && student.id) showApp();
})();
