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
  const answers = new Map();

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
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
          <p class="muted">${o.type === 'quiz' ? 'Викторина' : 'Олимпиада'} · ${o.questionCount} савол · ҳадди гузаштан ${o.passScore}%</p>
          <button type="button" class="btn primary" data-start="${esc(o.id)}">Оғоз</button>
        </div>
      `).join('');

      box.querySelectorAll('[data-start]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const oly = list.find((x) => x.id === btn.dataset.start);
          if (oly) startExam(oly);
        });
      });
    } catch (err) {
      box.innerHTML = `<p class="error">${esc(err.message)}</p>`;
    }
  }

  function startExam(oly) {
    currentOlympiad = oly;
    answers.clear();
    listView.classList.add('hidden');
    resultView.classList.add('hidden');
    examView.classList.remove('hidden');
    document.getElementById('examTitle').textContent = oly.title;
    document.getElementById('examMsg').classList.add('hidden');

    const box = document.getElementById('examQuestions');
    box.innerHTML = (oly.questions || []).map((q, idx) => `
      <div class="exam-q" data-qid="${q.id}">
        <h4>${idx + 1}. ${esc(q.text)}</h4>
        ${(q.options || []).map((opt, oi) => `
          <button type="button" class="exam-opt" data-qid="${q.id}" data-oi="${oi}">${esc(opt)}</button>
        `).join('')}
      </div>
    `).join('');

    updateProgress();

    box.querySelectorAll('.exam-opt').forEach((btn) => {
      btn.addEventListener('click', () => {
        const qid = Number(btn.dataset.qid);
        const oi = Number(btn.dataset.oi);
        answers.set(qid, oi);
        box.querySelectorAll(`.exam-opt[data-qid="${qid}"]`).forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
        updateProgress();
      });
    });
  }

  function updateProgress() {
    const total = currentOlympiad?.questions?.length || 0;
    document.getElementById('examProgress').textContent = `${answers.size}/${total}`;
  }

  document.getElementById('submitExamBtn').addEventListener('click', async () => {
    const msg = document.getElementById('examMsg');
    msg.classList.add('hidden');
    if (!currentOlympiad) return;

    const total = currentOlympiad.questions.length;
    if (answers.size < total) {
      if (!confirm('Баъзе саволҳо ҷавоб надоранд. Ба ҳар ҳол супоред?')) return;
    }

    const payloadAnswers = currentOlympiad.questions.map((q) => ({
      questionId: q.id,
      selected: answers.has(q.id) ? answers.get(q.id) : -1,
    }));

    try {
      const data = await api('/api/olympiads/' + currentOlympiad.id + '/submit', {
        method: 'POST',
        body: JSON.stringify({ studentId: student.id, answers: payloadAnswers }),
      });
      const r = data.result;
      examView.classList.add('hidden');
      resultView.classList.remove('hidden');
      document.getElementById('resultScore').textContent = r.score + '%';
      document.getElementById('resultDetail').textContent =
        `Дуруст: ${r.correct} аз ${r.total} · ҳадди гузаштан: ${r.passScore}%`;
      const st = document.getElementById('resultStatus');
      st.textContent = r.status === 'passed' ? 'Гузашт' : 'Нагузашт';
      st.className = 'badge' + (r.status === 'passed' ? '' : ' fail');
    } catch (err) {
      msg.textContent = err.message;
      msg.classList.remove('hidden');
      msg.classList.add('error');
    }
  });

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  if (student?.id) showApp();
})();
