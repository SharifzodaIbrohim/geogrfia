(() => {
  const API = '';
  const STUDENT_KEY = 'geo_student';
  const FP = (() => {
    try {
      return localStorage.getItem('geo_fp') || (localStorage.setItem('geo_fp', Math.random().toString(36).slice(2)), localStorage.getItem('geo_fp'));
    } catch {
      return 'anon';
    }
  })();

  let student = null;
  try {
    student = JSON.parse(localStorage.getItem(STUDENT_KEY) || 'null');
  } catch {
    student = null;
  }

  const loginView = document.getElementById('loginView');
  const appView = document.getElementById('appView');
  const listView = document.getElementById('listView');
  const examView = document.getElementById('examView');
  const resultView = document.getElementById('resultView');
  const answers = new Map();
  let currentQIndex = 0;
  let currentOlympiad = null;
  let examSession = null;
  let examTimerId = null;
  let autosaveTimer = null;
  let examEndsAt = null;

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    const res = await fetch(API + path, { ...options, headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function showApp() {
    loginView.classList.add('hidden');
    appView.classList.remove('hidden');
    const nameEl = document.getElementById('studentName');
    const metaEl = document.getElementById('studentMeta');
    if (nameEl) nameEl.textContent = student.fullName || student.name || 'Хонанда';
    if (metaEl) {
      metaEl.textContent =
        ' · ' + (student.className || '') +
        ' · ' + (student.school || '') +
        ' · ID: ' + (student.id || '');
    }
    loadLists();
  }

  function showLogin() {
    student = null;
    localStorage.removeItem(STUDENT_KEY);
    appView.classList.add('hidden');
    loginView.classList.remove('hidden');
  }

  document.getElementById('studentLoginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const err = document.getElementById('loginError');
    err?.classList.add('hidden');
    try {
      const id = document.getElementById('studentIdInput').value.trim();
      const data = await api('/api/student/login', {
        method: 'POST',
        body: JSON.stringify({ studentId: id }),
      });
      student = data.student || data;
      localStorage.setItem(STUDENT_KEY, JSON.stringify(student));
      showApp();
    } catch (ex) {
      if (err) {
        err.textContent = ex.message;
        err.classList.remove('hidden');
      }
    }
  });

  document.getElementById('logoutBtn')?.addEventListener('click', showLogin);
  document.getElementById('backToListBtn')?.addEventListener('click', () => {
    resultView.classList.add('hidden');
    examView.classList.add('hidden');
    listView.classList.remove('hidden');
    loadLists();
  });

  async function loadLists() {
    try {
      const data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(student.id));
      const olyBox = document.getElementById('olympiadList');
      const quizBox = document.getElementById('quizList');
      const emptyOly = document.getElementById('emptyOly');
      const emptyQuiz = document.getElementById('emptyQuiz');
      const olympiads = (data.olympiads || []).filter((o) => (o.type || 'olympiad') !== 'quiz');
      const quizzes = (data.olympiads || []).filter((o) => (o.type || '') === 'quiz');
      const quizzes2 = data.quizzes || [];

      function card(o, isQuiz) {
        return `
          <div class="oly-card">
            <h3>${esc(o.title)}</h3>
            <p class="muted">${isQuiz ? 'Викторина' : 'Олимпиада'} · ${o.questionCount || 0} савол · ҳад ${o.passScore || 70}%</p>
            <button type="button" class="btn primary" data-start="${esc(o.id)}">Оғоз</button>
          </div>`;
      }

      if (olyBox) {
        olyBox.innerHTML = olympiads.map((o) => card(o, false)).join('') || '';
        emptyOly?.classList.toggle('hidden', olympiads.length > 0);
      }
      const allQ = [...quizzes, ...quizzes2];
      if (quizBox) {
        quizBox.innerHTML = allQ.map((o) => card(o, true)).join('') || '';
        emptyQuiz?.classList.toggle('hidden', allQ.length > 0);
      }

      document.querySelectorAll('[data-start]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.start;
          const oly = [...olympiads, ...allQ].find((x) => String(x.id) === String(id));
          if (oly) await startExam(oly);
        });
      });
    } catch (err) {
      console.warn(err);
    }
  }

  function stopExamTimers() {
    if (examTimerId) clearInterval(examTimerId);
    if (autosaveTimer) clearInterval(autosaveTimer);
    examTimerId = null;
    autosaveTimer = null;
  }

  function tickExamTimer() {
    const el = document.getElementById('examTimer');
    if (!el) return;
    if (!examEndsAt) {
      el.textContent = '—';
      return;
    }
    const left = Math.max(0, examEndsAt - Date.now());
    const m = Math.floor(left / 60000);
    const s = Math.floor((left % 60000) / 1000);
    el.textContent = `${m}:${String(s).padStart(2, '0')}`;
    if (left <= 0) submitExam(true);
  }

  async function doAutosave() {
    if (!examSession || !currentOlympiad) return;
    const payload = {};
    (examSession.questions || []).forEach((q) => {
      let sel = getAnswer(q.id);
      if (sel != null) payload[String(q.originalIndex)] = sel;
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
    } catch (_) {}
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
      currentQIndex = 0;
      (data.questions || []).forEach((q) => {
        if (q.selected != null && q.selected !== undefined) answers.set(q.id, q.selected);
      });
      listView.classList.add('hidden');
      resultView.classList.add('hidden');
      examView.classList.remove('hidden');
      document.getElementById('examTitle').textContent = currentOlympiad.title;
      const msg = document.getElementById('examMsg');
      if (msg) msg.classList.add('hidden');
      if (data.endsAt) examEndsAt = new Date(data.endsAt).getTime();
      else if (data.durationSec) examEndsAt = Date.now() + data.durationSec * 1000;
      else examEndsAt = null;
      renderExamQuestions();
      stopExamTimers();
      tickExamTimer();
      examTimerId = setInterval(tickExamTimer, 500);
      autosaveTimer = setInterval(doAutosave, 15000);
    } catch (err) {
      alert(err.message || 'Хато');
    }
  }

  const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

  function answerKey(qid) {
    const num = Number(qid);
    return Number.isNaN(num) ? qid : num;
  }

  function setAnswer(qid, oi) {
    const key = answerKey(qid);
    answers.set(key, oi);
    answers.set(String(qid), oi);
    updateProgress();
    doAutosave();
  }

  function getAnswer(qid) {
    if (answers.has(qid)) return answers.get(qid);
    if (answers.has(String(qid))) return answers.get(String(qid));
    const num = Number(qid);
    if (!Number.isNaN(num) && answers.has(num)) return answers.get(num);
    return null;
  }

  function renderExamQuestions() {
    const pane = document.getElementById('examQuestionPane') || document.getElementById('examQuestions');
    const qs = currentOlympiad.questions || [];
    if (!pane || !qs.length) {
      if (pane) pane.innerHTML = '<p class="muted">Савол нест</p>';
      updateProgress();
      return;
    }
    if (currentQIndex < 0) currentQIndex = 0;
    if (currentQIndex >= qs.length) currentQIndex = qs.length - 1;

    const q = qs[currentQIndex];
    const selected = getAnswer(q.id);
    const opts = q.options || [];

    pane.innerHTML = `
      <div class="exam-q-num">Савол ${currentQIndex + 1} / ${qs.length}</div>
      <p class="exam-q-text">${esc(q.text)}</p>
      <div class="exam-opts" role="listbox" aria-label="Вариантҳо">
        ${opts.map((opt, oi) => `
          <button type="button" class="exam-opt-btn ${selected === oi ? 'selected' : ''}"
            data-oi="${oi}" data-qid="${esc(String(q.id))}">
            <span class="exam-opt-letter">${LETTERS[oi] || (oi + 1)}</span>
            <span class="exam-opt-label">${esc(opt)}</span>
          </button>
        `).join('')}
      </div>
    `;

    pane.querySelectorAll('.exam-opt-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const oi = Number(btn.dataset.oi);
        const qid = btn.dataset.qid;
        setAnswer(qid, oi);
        pane.querySelectorAll('.exam-opt-btn').forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
        renderDots();
      });
    });

    const prev = document.getElementById('examPrevBtn');
    const next = document.getElementById('examNextBtn');
    if (prev) prev.disabled = currentQIndex <= 0;
    if (next) {
      next.disabled = false;
      next.textContent = currentQIndex >= qs.length - 1 ? 'Охирин' : 'Next →';
    }
    updateProgress();
    renderDots();
  }

  function renderDots() {
    const dots = document.getElementById('examDots');
    const qs = currentOlympiad?.questions || [];
    if (!dots) return;
    dots.innerHTML = qs.map((q, i) => {
      const answered = getAnswer(q.id) != null;
      const cur = i === currentQIndex ? 'current' : '';
      const ans = answered ? 'answered' : '';
      return `<button type="button" class="exam-dot ${cur} ${ans}" data-qi="${i}" title="Савол ${i + 1}"></button>`;
    }).join('');
    dots.querySelectorAll('.exam-dot').forEach((d) => {
      d.addEventListener('click', () => {
        currentQIndex = Number(d.dataset.qi) || 0;
        renderExamQuestions();
      });
    });
  }

  function updateProgress() {
    const total = (currentOlympiad?.questions || []).length;
    const el = document.getElementById('examProgress');
    if (el) el.textContent = `Савол ${Math.min(currentQIndex + 1, total)} / ${total} · ҷавоб ${answers.size}/${total}`;
  }

  document.getElementById('examPrevBtn')?.addEventListener('click', () => {
    if (currentQIndex > 0) {
      currentQIndex -= 1;
      renderExamQuestions();
    }
  });

  document.getElementById('examNextBtn')?.addEventListener('click', () => {
    const total = (currentOlympiad?.questions || []).length;
    if (currentQIndex < total - 1) {
      currentQIndex += 1;
      renderExamQuestions();
    }
  });

  async function submitExam(auto) {
    if (!examSession || !currentOlympiad) return;
    stopExamTimers();
    const payload = {};
    (examSession.questions || []).forEach((q) => {
      const sel = getAnswer(q.id);
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

  document.getElementById('submitExamBtn')?.addEventListener('click', async () => {
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
