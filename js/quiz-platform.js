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

  let FP = localStorage.getItem('geo_fp');
  if (!FP) {
    FP = Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('geo_fp', FP);
  }

  const $ = (id) => document.getElementById(id);
  const views = {
    list: $('viewList'),
    take: $('viewTake'),
    result: $('viewResult'),
    history: $('viewHistory'),
  };

  function show(name) {
    Object.values(views).forEach((v) => v && v.classList.add('hidden'));
    if (views[name]) views[name].classList.remove('hidden');
  }

  function paintAuthBtn() {
    const btn = $('btnAuth');
    if (!btn) return;
    if (user) btn.textContent = user.name ? user.name.split(' ')[0] : 'Профил';
    else if (studentId) btn.textContent = 'ID ✓';
    else btn.textContent = 'Ворид';
  }

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) {
      headers['X-User-Token'] = token;
      headers['Authorization'] = 'Bearer ' + token;
    }
    if (studentId) headers['X-Student-Id'] = studentId;
    headers['X-Client-Fingerprint'] = FP;
    const res = await fetch(API + path, { ...options, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.reason || 'Хато');
    return data;
  }

  async function loadList() {
    const err = $('listError');
    const empty = $('listEmpty');
    if (err) err.classList.add('hidden');
    try {
      const data = await api('/api/quizzes');
      quizzes = data.quizzes || [];
      const box = $('quizList');
      if (!box) return;
      if (!quizzes.length) {
        box.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        return;
      }
      if (empty) empty.classList.add('hidden');
      box.innerHTML = quizzes.map((q) => `
        <article class="q-quiz-item">
          <h3>${esc(q.title)}</h3>
          <p>${esc(q.description || '')}</p>
          <p>
            <span class="tag">${esc(q.source || 'quiz')}</span>
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
      if (err) {
        err.textContent = e.message;
        err.classList.remove('hidden');
      }
      console.error('loadList', e);
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
        id: data.quizId || id,
        title: data.title,
        questions: data.questions || [],
        passScore: data.passScore,
        timeLimitSec: data.timeLimitSec,
        source: data.source || 'quiz',
      };
      answers = {};
      qIndex = 0;
      endsAt = data.endsAt ? new Date(data.endsAt) : null;
      if ($('takeTitle')) $('takeTitle').textContent = data.title || 'Викторина';
      if ($('takeMeta')) $('takeMeta').textContent = `${currentQuiz.questions.length} савол · ҳад ${data.passScore}%`;
      renderQuestion();
      startTimer();
      show('take');
    } catch (e) {
      const msg = String(e.message || '');
      if (/Google|google|рад|Student|ID|хонанда|ворид/i.test(msg)) openAuth(msg);
      else alert(msg);
    }
  }

  function renderQuestion() {
    const qs = currentQuiz.questions;
    const q = qs[qIndex];
    if (!q) return;
    const qid = String(q.id || qIndex + 1);
    const selected = answers[qid];
    if ($('qProgress')) $('qProgress').textContent = `${qIndex + 1} / ${qs.length}`;
    if ($('btnPrev')) $('btnPrev').disabled = qIndex === 0;
    if ($('btnNext')) $('btnNext').disabled = qIndex >= qs.length - 1;
    const box = $('questionBox');
    if (!box) return;
    box.innerHTML = `
      <p><strong>Савол ${qIndex + 1}</strong></p>
      <p>${esc(q.text)}</p>
      ${(q.options || []).map((opt, i) => `
        <button type="button" class="q-option ${selected === i ? 'selected' : ''}" data-opt="${i}">${esc(opt)}</button>
      `).join('')}
    `;
    box.querySelectorAll('[data-opt]').forEach((btn) => {
      btn.addEventListener('click', () => {
        answers[qid] = Number(btn.dataset.opt);
        renderQuestion();
      });
    });
  }

  function startTimer() {
    stopTimer();
    const box = $('timerBox');
    if (!box) return;
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
    let answersPayload;
    if (currentQuiz.source === 'olympiad') {
      answersPayload = {};
      (currentQuiz.questions || []).forEach((q, i) => {
        const sel = answers[String(q.id || i + 1)];
        if (sel == null) return;
        const key = q.originalIndex != null ? q.originalIndex : i;
        answersPayload[String(key)] = sel;
      });
    } else {
      answersPayload = currentQuiz.questions.map((q, i) => ({
        questionId: q.id || (i + 1),
        selected: answers[String(q.id || i + 1)] ?? null,
      }));
    }
    try {
      const data = await api('/api/quizzes/' + currentQuiz.id + '/submit', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: attempt.attemptId || attempt.sessionId,
          sessionId: attempt.sessionId,
          sessionToken: attempt.sessionToken,
          answers: answersPayload,
        }),
      });
      const r = data.result || {};
      if ($('resultScore')) $('resultScore').textContent = (r.score ?? '—') + '%';
      const st = $('resultStatus');
      if (st) {
        st.textContent = r.status === 'passed' ? 'Гузашт' : 'Нагузашт';
        st.className = 'q-badge ' + (r.status === 'passed' ? 'ok' : 'fail');
      }
      const rd = $('resultDetail');
      if (rd) rd.textContent =
        `${r.correct}/${r.total} дуруст · ҳад ${r.passScore}%` +
        (r.timedOut ? ' · вақт тамом' : '') +
        (auto ? ' · худкор' : '');
      show('result');
    } catch (e) {
      alert(e.message);
    }
  }

  async function loadHistory() {
    const list = $('historyList');
    const hint = $('historyHint');
    if (!token) {
      if (hint) hint.textContent = 'Барои таърих бо Google ворид шавед.';
      if (list) list.innerHTML = '';
      return;
    }
    try {
      const data = await api('/api/me/quiz-history');
      const rows = data.history || [];
      if (hint) hint.textContent = rows.length ? 'Натиҷаҳои охирин:' : 'Ҳанӯз натиҷа нест.';
      if (list) list.innerHTML = rows.map((h) => `
        <div class="q-hist">
          <div>
            <strong>${esc(h.title || h.quizId)}</strong>
            <div class="q-muted">${esc((h.finishedAt || '').slice(0, 19).replace('T', ' '))}</div>
          </div>
          <div><span class="q-badge ${h.status === 'passed' ? 'ok' : 'fail'}">${h.score}%</span></div>
        </div>
      `).join('');
    } catch (e) {
      if (hint) hint.textContent = e.message;
      if (list) list.innerHTML = '';
    }
  }

  function openAuth(msg) {
    const ov = $('authOverlay');
    if (!ov) return;
    ov.classList.remove('hidden');
    const am = $('authMsg');
    if (am) {
      if (msg) { am.textContent = msg; am.classList.remove('hidden'); }
      else am.classList.add('hidden');
    }
    if (user) {
      if ($('authProfile')) $('authProfile').classList.remove('hidden');
      if ($('googleBtnWrap')) $('googleBtnWrap').classList.add('hidden');
      if ($('authName')) $('authName').textContent = user.name || '';
      if ($('authEmail')) $('authEmail').textContent = user.email || '';
    } else {
      if ($('authProfile')) $('authProfile').classList.add('hidden');
      if ($('googleBtnWrap')) $('googleBtnWrap').classList.remove('hidden');
      initGoogle();
    }
    if ($('studentIdInput')) $('studentIdInput').value = studentId;
  }

  function closeAuth() {
    const ov = $('authOverlay');
    if (ov) ov.classList.add('hidden');
  }

  async function initGoogle(attempt) {
    attempt = attempt || 0;
    try {
      const st = await api('/api/auth/google/status');
      googleClientId = st.clientId || st.client_id;
      if (!st.configured || !googleClientId) {
        if ($('googleBtnWrap')) {
          const w = $('googleBtnWrap');
          if (!w.querySelector('.g-fallback')) {
            const p = document.createElement('p');
            p.className = 'q-muted g-fallback';
            p.textContent = 'Google Sign-In ҳоло танзим нашудааст.';
            w.appendChild(p);
          }
        }
        return;
      }
      if (!window.google || !window.google.accounts || !window.google.accounts.id) {
        if (attempt < 12) {
          setTimeout(function () { initGoogle(attempt + 1); }, 400);
        }
        return;
      }
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (resp) => {
          try {
            if (!resp || !resp.credential) throw new Error('Google credential нест');
            const data = await api('/api/auth/google', {
              method: 'POST',
              body: JSON.stringify({ idToken: resp.credential, credential: resp.credential }),
            });
            token = data.token || data.accessToken;
            user = data.user || data.profile || null;
            if (!token) throw new Error(data.error || 'Token нест');
            localStorage.setItem(USER_KEY, token);
            localStorage.setItem(USER_OBJ, JSON.stringify(user || {}));
            localStorage.setItem('userToken', token);
            localStorage.setItem('currentUser', JSON.stringify(user || {}));
            paintAuthBtn();
            closeAuth();
            const b = $('guestBanner');
            if (b) b.style.display = 'none';
            loadList();
          } catch (e) {
            if ($('authMsg')) {
              $('authMsg').textContent = e.message || 'Хатои Google login';
              $('authMsg').classList.remove('hidden');
            }
          }
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      const el = $('googleSignInBtn');
      if (!el) return;
      el.innerHTML = '';
      window.google.accounts.id.renderButton(el, {
        theme: 'outline',
        size: 'large',
        width: 280,
        text: 'signin_with',
        shape: 'rectangular',
      });
    } catch (e) {
      console.warn('initGoogle', e);
      if (attempt < 8) setTimeout(function () { initGoogle(attempt + 1); }, 500);
    }
  }

  function esc(s) {
    const map = {
      '&': String.fromCharCode(38) + 'amp;',
      '<': String.fromCharCode(38) + 'lt;',
      '>': String.fromCharCode(38) + 'gt;',
      '"': String.fromCharCode(38) + 'quot;',
      "'": String.fromCharCode(38) + '#39;',
    };
    return String(s ?? '').replace(/[&<>"']/g, (ch) => map[ch]);
  }

  function on(id, evt, fn) {
    const el = $(id);
    if (el) el.addEventListener(evt, fn);
  }

  on('btnBackList', 'click', () => { stopTimer(); show('list'); });
  on('btnPrev', 'click', () => { if (qIndex > 0) { qIndex--; renderQuestion(); } });
  on('btnNext', 'click', () => {
    if (currentQuiz && qIndex < currentQuiz.questions.length - 1) { qIndex++; renderQuestion(); }
  });
  on('btnSubmit', 'click', () => {
    if (!confirm('Супоред?')) return;
    submitQuiz(false);
  });
  on('btnAgain', 'click', () => { show('list'); loadList(); });
  on('btnBackFromResult', 'click', () => { show('list'); loadList(); });
  on('btnToHistory', 'click', () => { show('history'); loadHistory(); });
  on('btnHistory', 'click', () => { show('history'); loadHistory(); });
  on('btnBackFromHistory', 'click', () => show('list'));
  on('btnAuth', 'click', () => openAuth());
  on('authClose', 'click', closeAuth);
  on('btnLogout', 'click', () => {
    token = ''; user = null;
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(USER_OBJ);
    localStorage.removeItem('userToken');
    localStorage.removeItem('currentUser');
    paintAuthBtn(); closeAuth();
  });
  function saveStudentId() {
    const input = $('studentIdInput');
    if (!input) return;
    studentId = input.value.trim();
    if (studentId) localStorage.setItem(STUDENT_KEY, studentId);
    else localStorage.removeItem(STUDENT_KEY);
    paintAuthBtn(); closeAuth();
  }
  on('btnSaveStudent', 'click', saveStudentId);
  on('btnSaveStudentId', 'click', saveStudentId);
  on('btnGuestLogin', 'click', () => openAuth());

  paintAuthBtn();
  loadList();
  setTimeout(initGoogle, 500);
})();
