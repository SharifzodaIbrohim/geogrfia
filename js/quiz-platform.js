(() => {
  const API = '';
  const USER_KEY = 'geo_user_token';
  const USER_OBJ = 'geo_user';
  const STUDENT_KEY = 'geo_student_id';

  let token = localStorage.getItem(USER_KEY) || localStorage.getItem('userToken') || '';
  let user = null;
  try {
    user = JSON.parse(localStorage.getItem(USER_OBJ) || localStorage.getItem('currentUser') || 'null');
  } catch { user = null; }
  if (token && !localStorage.getItem(USER_KEY)) localStorage.setItem(USER_KEY, token);
  if (user && !localStorage.getItem(USER_OBJ)) localStorage.setItem(USER_OBJ, JSON.stringify(user));
  let studentId = localStorage.getItem(STUDENT_KEY) || '';

  let quizzes = [];
  let currentQuiz = null;
  let attempt = null;
  let answers = {};
  let qIndex = 0;
  let timerId = null;
  let endsAt = null;
  let googleClientId = null;

  const $ = (id) => document.getElementById(id);
  const views = {
    list: $('viewList'),
    take: $('viewTake'),
    result: $('viewResult'),
    history: $('viewHistory'),
  };

  function show(name) {
    Object.values(views).forEach((v) => v.classList.add('hidden'));
    views[name].classList.remove('hidden');
  }

  function paintAuthBtn() {
    const btn = $('btnAuth');
    if (user) {
      btn.textContent = user.name ? user.name.split(' ')[0] : 'Профил';
    } else if (studentId) {
      btn.textContent = 'ID ✓';
    } else {
      btn.textContent = 'Ворид';
    }
  }

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['X-User-Token'] = token;
    if (studentId) headers['X-Student-Id'] = studentId;
    const res = await fetch(API + path, { ...options, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.reason || 'Хато');
    return data;
  }

  async function loadList() {
    const err = $('listError');
    const empty = $('listEmpty');
    err.classList.add('hidden');
    try {
      const data = await api('/api/quizzes');
      quizzes = data.quizzes || [];
      const box = $('quizList');
      if (!quizzes.length) {
        box.innerHTML = '';
        empty.classList.remove('hidden');
        return;
      }
      empty.classList.add('hidden');
      box.innerHTML = quizzes.map((q) => `
        <article class="q-quiz-item">
          <h3>${esc(q.title)}</h3>
          <p>${esc(q.description || '')}</p>
          <p>
            <span class="tag">${esc(q.accessMode || 'public')}</span>
            <span class="tag">${q.questionCount || 0} савол</span>
            ${q.timeLimitSec ? `<span class="tag">${Math.round(q.timeLimitSec / 60)} дақ</span>` : ''}
            <span class="tag">ҳад ${q.passScore || 70}%</span>
          </p>
          <div class="q-row">
            <button type="button" class="q-btn primary" data-start="${esc(q.id)}">Оғоз</button>
          </div>
        </article>
      `).join('');
      box.querySelectorAll('[data-start]').forEach((btn) => {
        btn.addEventListener('click', () => startQuiz(btn.dataset.start));
      });
    } catch (e) {
      err.textContent = e.message;
      err.classList.remove('hidden');
    }
  }

  async function startQuiz(id) {
    try {
      const data = await api('/api/quizzes/' + id + '/start', {
        method: 'POST',
        body: JSON.stringify(studentId ? { studentId } : {}),
      });
      attempt = data;
      currentQuiz = {
        id: data.quizId,
        title: data.title,
        questions: data.questions || [],
        passScore: data.passScore,
        timeLimitSec: data.timeLimitSec,
      };
      answers = {};
      qIndex = 0;
      endsAt = data.endsAt ? new Date(data.endsAt) : null;
      $('takeTitle').textContent = data.title || 'Викторина';
      $('takeMeta').textContent = `${currentQuiz.questions.length} савол · ҳад ${data.passScore}%`;
      renderQuestion();
      startTimer();
      show('take');
    } catch (e) {
      if (String(e.message).includes('Google') || String(e.message).includes('google') || String(e.message).includes('рад')) {
        openAuth(e.message);
      } else {
        alert(e.message);
      }
    }
  }

  function renderQuestion() {
    const qs = currentQuiz.questions;
    const q = qs[qIndex];
    if (!q) return;
    const qid = String(q.id || qIndex + 1);
    const selected = answers[qid];
    $('qProgress').textContent = `${qIndex + 1} / ${qs.length}`;
    $('btnPrev').disabled = qIndex === 0;
    $('btnNext').disabled = qIndex >= qs.length - 1;
    $('questionBox').innerHTML = `
      <p><strong>Савол ${qIndex + 1}</strong></p>
      <p>${esc(q.text)}</p>
      ${(q.options || []).map((opt, i) => `
        <button type="button" class="q-option ${selected === i ? 'selected' : ''}" data-opt="${i}">${esc(opt)}</button>
      `).join('')}
    `;
    $('questionBox').querySelectorAll('[data-opt]').forEach((btn) => {
      btn.addEventListener('click', () => {
        answers[qid] = Number(btn.dataset.opt);
        renderQuestion();
      });
    });
  }

  function startTimer() {
    stopTimer();
    const box = $('timerBox');
    if (!endsAt) {
      box.textContent = 'бе маҳдудият';
      box.className = 'q-timer';
      return;
    }
    const tick = () => {
      const ms = endsAt - Date.now();
      if (ms <= 0) {
        box.textContent = '00:00';
        box.className = 'q-timer danger';
        stopTimer();
        submitQuiz(true);
        return;
      }
      const sec = Math.ceil(ms / 1000);
      const m = String(Math.floor(sec / 60)).padStart(2, '0');
      const s = String(sec % 60).padStart(2, '0');
      box.textContent = `${m}:${s}`;
      box.className = 'q-timer' + (sec < 30 ? ' danger' : sec < 60 ? ' warn' : '');
    };
    tick();
    timerId = setInterval(tick, 500);
  }

  function stopTimer() {
    if (timerId) clearInterval(timerId);
    timerId = null;
  }

  async function submitQuiz(auto) {
    if (!attempt || !currentQuiz) return;
    stopTimer();
    const payloadAnswers = currentQuiz.questions.map((q, i) => ({
      questionId: q.id || (i + 1),
      selected: answers[String(q.id || i + 1)] ?? null,
    }));
    try {
      const data = await api('/api/quizzes/' + currentQuiz.id + '/submit', {
        method: 'POST',
        body: JSON.stringify({ attemptId: attempt.attemptId, answers: payloadAnswers }),
      });
      const r = data.result || {};
      $('resultScore').textContent = (r.score ?? '—') + '%';
      const st = $('resultStatus');
      st.textContent = r.status === 'passed' ? 'Гузашт' : 'Нагузашт';
      st.className = 'q-badge ' + (r.status === 'passed' ? 'ok' : 'fail');
      $('resultDetail').textContent =
        `${r.correct}/${r.total} дуруст · ҳад ${r.passScore}%` +
        (r.timedOut ? ' · вақт тамом' : '') +
        (auto ? ' · худкор супорида шуд' : '');
      show('result');
    } catch (e) {
      alert(e.message);
    }
  }

  async function loadHistory() {
    const list = $('historyList');
    const hint = $('historyHint');
    if (!token) {
      hint.textContent = 'Барои таърих бо Google ворид шавед.';
      list.innerHTML = '';
      return;
    }
    try {
      const data = await api('/api/me/quiz-history');
      const rows = data.history || [];
      hint.textContent = rows.length ? 'Натиҷаҳои охирин:' : 'Ҳанӯз натиҷа нест.';
      list.innerHTML = rows.map((h) => `
        <div class="q-hist">
          <div>
            <strong>${esc(h.title || h.quizId)}</strong>
            <div class="q-muted">${esc((h.finishedAt || '').slice(0, 19).replace('T', ' '))}</div>
          </div>
          <div>
            <span class="q-badge ${h.status === 'passed' ? 'ok' : 'fail'}">${h.score}%</span>
          </div>
        </div>
      `).join('');
    } catch (e) {
      hint.textContent = e.message;
      list.innerHTML = '';
    }
  }

  function openAuth(msg) {
    $('authOverlay').classList.remove('hidden');
    const am = $('authMsg');
    if (msg) { am.textContent = msg; am.classList.remove('hidden'); }
    else am.classList.add('hidden');
    if (user) {
      $('authProfile').classList.remove('hidden');
      $('googleBtnWrap').classList.add('hidden');
      $('authName').textContent = user.name || '';
      $('authEmail').textContent = user.email || '';
    } else {
      $('authProfile').classList.add('hidden');
      $('googleBtnWrap').classList.remove('hidden');
      initGoogle();
    }
    $('studentIdInput').value = studentId;
  }

  function closeAuth() {
    $('authOverlay').classList.add('hidden');
  }

  async function initGoogle() {
    try {
      const st = await api('/api/auth/google/status');
      googleClientId = st.clientId;
      if (!st.configured || !window.google) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (resp) => {
          try {
            const data = await api('/api/auth/google', {
              method: 'POST',
              body: JSON.stringify({ idToken: resp.credential }),
            });
            token = data.token;
            user = data.user;
            localStorage.setItem(USER_KEY, token);
            localStorage.setItem(USER_OBJ, JSON.stringify(user));
            localStorage.setItem('userToken', token);
            localStorage.setItem('currentUser', JSON.stringify(user));
            paintAuthBtn();
            closeAuth();
          } catch (e) {
            $('authMsg').textContent = e.message;
            $('authMsg').classList.remove('hidden');
          }
        },
      });
      const el = $('googleSignInBtn');
      el.innerHTML = '';
      window.google.accounts.id.renderButton(el, { theme: 'outline', size: 'large', width: 280 });
    } catch (e) {
      console.warn(e);
    }
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&', '<': '<', '>': '>', '"': '"', "'": '&#39;' }[c]));
  }

  $('btnBackList').addEventListener('click', () => { stopTimer(); show('list'); });
  $('btnPrev').addEventListener('click', () => { if (qIndex > 0) { qIndex--; renderQuestion(); } });
  $('btnNext').addEventListener('click', () => {
    if (qIndex < currentQuiz.questions.length - 1) { qIndex++; renderQuestion(); }
  });
  $('btnSubmit').addEventListener('click', () => {
    if (!confirm('Супоред?')) return;
    submitQuiz(false);
  });
  $('btnAgain').addEventListener('click', () => { show('list'); loadList(); });
  $('btnToHistory').addEventListener('click', () => { show('history'); loadHistory(); });
  $('btnHistory').addEventListener('click', () => { show('history'); loadHistory(); });
  $('btnBackFromHistory').addEventListener('click', () => show('list'));
  $('btnAuth').addEventListener('click', () => openAuth());
  $('authClose').addEventListener('click', closeAuth);
  $('btnLogout').addEventListener('click', () => {
    token = '';
    user = null;
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(USER_OBJ);
    localStorage.removeItem('userToken');
    localStorage.removeItem('currentUser');
    paintAuthBtn();
    closeAuth();
  });
  $('btnSaveStudent').addEventListener('click', () => {
    studentId = $('studentIdInput').value.trim();
    if (studentId) localStorage.setItem(STUDENT_KEY, studentId);
    else localStorage.removeItem(STUDENT_KEY);
    paintAuthBtn();
    closeAuth();
  });

  paintAuthBtn();
  loadList();
  setTimeout(initGoogle, 500);
})();
