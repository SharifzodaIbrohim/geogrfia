(() => {
  const API = '';
  const STUDENT_KEY = 'geo_student';
  const FP = (() => {
    try {
      return localStorage.getItem('geo_fp') || (localStorage.setItem('geo_fp', Math.random().toString(36).slice(2)), localStorage.getItem('geo_fp'));
    } catch { return 'anon'; }
  })();
  let student = null;
  try { student = JSON.parse(localStorage.getItem(STUDENT_KEY) || 'null'); } catch { student = null; }
  const loginView = document.getElementById('loginView');
  const appView = document.getElementById('appView');
  const listView = document.getElementById('listView');
  const examView = document.getElementById('examView');
  const resultView = document.getElementById('resultView');
  const answers = new Map();
  let currentQIndex = 0, currentOlympiad = null, examSession = null, examTimerId = null, autosaveTimer = null, examEndsAt = null;

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
    if (metaEl) metaEl.textContent = ' · ' + (student.className || '') + ' · ' + (student.school || '') + ' · ID: ' + (student.id || '');
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
        body: JSON.stringify({ id: id, studentId: id }),
      });
      student = data.student || data;
      localStorage.setItem(STUDENT_KEY, JSON.stringify(student));
      showApp();
    } catch (ex) {
      if (err) { err.textContent = ex.message; err.classList.remove('hidden'); }
    }
  });
  document.getElementById('logoutBtn')?.addEventListener('click', showLogin);
  document.getElementById('backToListBtn')?.addEventListener('click', () => {
    resultView.classList.add('hidden'); examView.classList.add('hidden'); listView.classList.remove('hidden'); loadLists();
  });

  async function loadLists() {
    try {
      let data = { olympiads: [], quizzes: [] };
      try {
        data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(student.id));
      } catch (e1) {
        try {
          const act = await api('/api/olympiads/active');
          const items = act.olympiads || act.items || (Array.isArray(act) ? act : []);
          data.olympiads = items.filter((o) => (o.type || 'olympiad').toLowerCase() !== 'quiz');
          data.quizzes = items.filter((o) => (o.type || '').toLowerCase() === 'quiz');
        } catch (e2) { console.warn(e1, e2); }
      }
      if ((!data.olympiads || !data.olympiads.length) && (!data.quizzes || !data.quizzes.length)) {
        try {
          const act = await api('/api/olympiads/active');
          const items = act.olympiads || act.items || (Array.isArray(act) ? act : []);
          data.olympiads = items.filter((o) => (o.type || 'olympiad').toLowerCase() !== 'quiz');
          data.quizzes = items.filter((o) => (o.type || '').toLowerCase() === 'quiz');
        } catch (_) {}
      }
      const olyBox = document.getElementById('olympiadList');
      const quizBox = document.getElementById('quizList');
      const emptyOly = document.getElementById('emptyOly');
      const emptyQuiz = document.getElementById('emptyQuiz');
      const rawOly = data.olympiads || [];
      const olympiads = rawOly.filter((o) => (o.type || 'olympiad').toLowerCase() !== 'quiz');
      const fromOly = rawOly.filter((o) => (o.type || '').toLowerCase() === 'quiz');
      const quizzes2 = data.quizzes || [];
      const seenQ = new Set();
      const quizzes = [];
      for (const q of [...fromOly, ...quizzes2]) {
        const id = String(q.id || '');
        if (!id || seenQ.has(id)) continue;
        seenQ.add(id);
        quizzes.push(q);
      }
      function card(o, isQuiz) {
        return `<div class="oly-card"><h3>${esc(o.title)}</h3><p class="muted">${isQuiz ? 'Викторина' : 'Олимпиада'} · ${o.questionCount || 0} савол · ҳад ${o.passScore || 70}%</p><button type="button" class="btn primary" data-start="${esc(o.id)}">Оғоз</button></div>`;
      }
      if (olyBox) { olyBox.innerHTML = olympiads.map((o) => card(o, false)).join('') || ''; emptyOly?.classList.toggle('hidden', olympiads.length > 0); }
      if (quizBox) { quizBox.innerHTML = quizzes.map((o) => card(o, true)).join('') || ''; emptyQuiz?.classList.toggle('hidden', quizzes.length > 0); }
      document.querySelectorAll('[data-start]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.dataset.start;
          const oly = [...olympiads, ...quizzes].find((x) => String(x.id) === String(id));
          if (oly) await startExam(oly);
        });
      });
    } catch (err) { console.warn(err); }
  }

  function stopExamTimers() {
    if (examTimerId) clearInterval(examTimerId);
    if (autosaveTimer) clearInterval(autosaveTimer);
    examTimerId = null; autosaveTimer = null;
  }
  function tickExamTimer() {
    const el = document.getElementById('examTimer');
    if (!el) return;
    if (!examEndsAt) { el.textContent = '—'; return; }
    const left = Math.max(0, examEndsAt - Date.now());
    const m = Math.floor(left / 60000), s = Math.floor((left % 60000) / 1000);
    el.textContent = `${m}:${String(s).padStart(2, '0')}`;
    if (left <= 0) submitExam(true);
  }
  async function doAutosave() {
    if (!examSession || !currentOlympiad) return;
    const payload = {};
    (examSession.questions || []).forEach((q) => {
      let sel = getAnswer(q.id);
      if (sel != null) {
        const oi = q.originalIndex != null ? q.originalIndex : q.id;
        payload[String(oi)] = sel;
        if (q.id != null) payload[String(q.id)] = sel;
      }
    });
    try {
      const res = await api('/api/olympiads/' + currentOlympiad.id + '/autosave', {
        method: 'POST', headers: { 'X-Client-Fingerprint': FP },
        body: JSON.stringify({ sessionId: examSession.sessionId, sessionToken: examSession.sessionToken, answers: payload }),
      });
      if (res && res.expiresAt) examEndsAt = new Date(res.expiresAt).getTime();
      else if (res && res.remainingSec != null) examEndsAt = Date.now() + Number(res.remainingSec) * 1000;
    } catch (_) {}
  }
  async function startExam(oly) {
    try {
      const data = await api('/api/olympiads/' + oly.id + '/start', {
        method: 'POST', headers: { 'X-Client-Fingerprint': FP },
        body: JSON.stringify({ studentId: student.id }),
      });
      examSession = data;
      currentOlympiad = { ...oly, id: data.olympiadId || oly.id, questions: data.questions || [], title: data.title || oly.title, passScore: data.passScore };
      answers.clear(); currentQIndex = 0;
      (data.questions || []).forEach((q) => { if (q.selected != null) answers.set(q.id, q.selected); });
      listView.classList.add('hidden'); resultView.classList.add('hidden'); examView.classList.remove('hidden');
      document.getElementById('examTitle').textContent = currentOlympiad.title;
      document.getElementById('examMsg')?.classList.add('hidden');
      if (data.expiresAt) examEndsAt = new Date(data.expiresAt).getTime();
      else if (data.endsAt) examEndsAt = new Date(data.endsAt).getTime();
      else if (data.remainingSec != null) examEndsAt = Date.now() + Number(data.remainingSec) * 1000;
      else if (data.durationSec) examEndsAt = Date.now() + data.durationSec * 1000;
      else examEndsAt = null;
      renderExamQuestions(); stopExamTimers(); tickExamTimer();
      examTimerId = setInterval(tickExamTimer, 500);
      autosaveTimer = setInterval(doAutosave, 15000);
    } catch (err) { alert(err.message || 'Хато'); }
  }
  const LETTERS = ['A','B','C','D','E','F','G','H'];
  function answerKey(qid) { const num = Number(qid); return Number.isNaN(num) ? qid : num; }
  function setAnswer(qid, val) {
    answers.set(answerKey(qid), val);
    answers.set(String(qid), val);
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
  function isAnswered(qid) {
    const v = getAnswer(qid);
    if (v == null) return false;
    if (typeof v === 'object' && !Array.isArray(v)) {
      return Object.keys(v).some((k) => v[k] !== '' && v[k] != null);
    }
    if (typeof v === 'string') return v.trim().length > 0;
    return true;
  }
  function typeLabel(t) {
    t = String(t || 'single').toLowerCase();
    if (t === 'short') return 'Ҷавоби кӯтоҳ / рақамӣ';
    if (t === 'matching') return 'Мувофиқат';
    if (t === 'text') return 'Шарҳ / мафҳум';
    return 'Интихоб';
  }
  function renderExamQuestions() {
    const pane = document.getElementById('examQuestionPane') || document.getElementById('examQuestions');
    const qs = currentOlympiad.questions || [];
    if (!pane || !qs.length) { if (pane) pane.innerHTML = '<p class="muted">Савол нест</p>'; updateProgress(); return; }
    if (currentQIndex < 0) currentQIndex = 0;
    if (currentQIndex >= qs.length) currentQIndex = qs.length - 1;
    const q = qs[currentQIndex];
    const qid = String(q.id);
    const qtype = String(q.type || 'single').toLowerCase();
    const selected = getAnswer(q.id);
    let body = '';

    if (qtype === 'short') {
      const val = selected != null ? String(selected) : '';
      body = `<div class="exam-input-wrap" style="margin-top:.75rem">
        <label class="muted" style="display:block;margin-bottom:.35rem">Ҷавоби худро нависед (матн ё рақам)</label>
        <input type="text" id="ansInput" class="exam-text-input" inputmode="text"
          value="${esc(val)}" placeholder="Ҷавоб…" autocomplete="off" />
      </div>`;
    } else if (qtype === 'text') {
      const val = selected != null ? String(selected) : '';
      body = `<div class="exam-input-wrap" style="margin-top:.75rem">
        <label class="muted" style="display:block;margin-bottom:.35rem">Шарҳ / мафҳумро нависед</label>
        <textarea id="ansInput" class="exam-text-input" rows="5" style="resize:vertical;min-height:120px"
          placeholder="Ҷавоби муфассал…">${esc(val)}</textarea>
      </div>`;
    } else if (qtype === 'matching') {
      const left = q.leftItems || [];
      const right = q.rightItems || [];
      const cur = (selected && typeof selected === 'object') ? selected : {};
      body = `<div class="exam-match">
        <p class="muted exam-match-hint">Барои ҳар сатр ҷавоби мувофиқро аз рӯйхат интихоб кунед</p>
        ${left.map((L, li) => {
          const sel = cur[String(li)] != null ? String(cur[String(li)]) : (cur[li] != null ? String(cur[li]) : '');
          return `<div class="exam-match-row">
            <span class="exam-match-left"><b>${li + 1}.</b> ${esc(L)}</span>
            <select data-left="${li}" class="match-select exam-match-select">
              <option value="">— интихоб —</option>
              ${right.map((r, ri) => `<option value="${ri}" ${sel === String(ri) ? 'selected' : ''}>${esc(LETTERS[ri] || (ri + 1))}. ${esc(r)}</option>`).join('')}
            </select>
          </div>`;
        }).join('')}
      </div>`;
    } else {
      const opts = q.options || [];
      body = `<div class="exam-opts" role="listbox">${opts.map((opt, oi) => {
        const lab = typeof opt === 'string' ? opt : (opt && (opt.text || opt.label)) || String(opt);
        return `<button type="button" class="exam-opt-btn ${selected === oi ? 'selected' : ''}" data-oi="${oi}" data-qid="${esc(qid)}"><span class="exam-opt-letter">${LETTERS[oi] || (oi + 1)}</span><span class="exam-opt-label">${esc(lab)}</span></button>`;
      }).join('')}</div>`;
    }

    pane.innerHTML = `<div class="exam-q-num">Савол ${currentQIndex + 1} / ${qs.length} · <span class="muted">${esc(typeLabel(qtype))}</span></div>
      <p class="exam-q-text">${esc(q.text)}</p>${body}`;

    if (qtype === 'short' || qtype === 'text') {
      const inp = pane.querySelector('#ansInput');
      if (inp) {
        const save = () => setAnswer(qid, inp.value);
        inp.addEventListener('input', save);
        inp.addEventListener('change', save);
        setTimeout(() => { try { inp.focus(); } catch (e) {} }, 50);
      }
    } else if (qtype === 'matching') {
      pane.querySelectorAll('.match-select').forEach((sel) => {
        sel.addEventListener('change', () => {
          const map = Object.assign({}, getAnswer(qid) && typeof getAnswer(qid) === 'object' ? getAnswer(qid) : {});
          const li = String(sel.dataset.left);
          if (sel.value === '') delete map[li];
          else map[li] = Number(sel.value);
          setAnswer(qid, map);
          renderDots();
        });
      });
    } else {
      pane.querySelectorAll('.exam-opt-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          setAnswer(btn.dataset.qid, Number(btn.dataset.oi));
          pane.querySelectorAll('.exam-opt-btn').forEach((b) => b.classList.remove('selected'));
          btn.classList.add('selected');
          renderDots();
        });
      });
    }

    const prev = document.getElementById('examPrevBtn');
    const next = document.getElementById('examNextBtn');
    if (prev) prev.disabled = currentQIndex <= 0;
    if (next) { next.disabled = false; next.textContent = currentQIndex >= qs.length - 1 ? 'Охирин' : 'Next →'; }
    updateProgress();
    renderDots();
  }
  function renderDots() {
    const dots = document.getElementById('examDots');
    const qs = currentOlympiad?.questions || [];
    if (!dots) return;
    dots.innerHTML = qs.map((q, i) => {
      const answered = isAnswered(q.id);
      return `<button type="button" class="exam-dot ${i === currentQIndex ? 'current' : ''} ${answered ? 'done' : ''}" data-i="${i}" title="Савол ${i + 1}"></button>`;
    }).join('');
    dots.querySelectorAll('.exam-dot').forEach((b) => {
      b.addEventListener('click', () => { currentQIndex = Number(b.dataset.i); renderExamQuestions(); });
    });
  }
  function updateProgress() {
    const qs = currentOlympiad?.questions || [];
    const done = qs.filter((q) => isAnswered(q.id)).length;
    const el = document.getElementById('examProgress');
    if (el) el.textContent = `Савол ${currentQIndex + 1} / ${qs.length} · ҷавоб: ${done}`;
  }

  document.getElementById('examPrevBtn')?.addEventListener('click', () => { if (currentQIndex > 0) { currentQIndex -= 1; renderExamQuestions(); } });
  document.getElementById('examNextBtn')?.addEventListener('click', () => {
    const total = (currentOlympiad?.questions || []).length;
    if (currentQIndex < total - 1) { currentQIndex += 1; renderExamQuestions(); }
  });
  function showResult(r, auto) {
    r = r || {};
    if (r.result && typeof r.result === 'object') r = Object.assign({}, r, r.result);
    examView.classList.add('hidden'); resultView.classList.remove('hidden');
    const pending = !!(r.pendingReview || r.hideScore || r.message);
    const total = r.total != null ? Number(r.total) : null;
    const emptyScore = (r.score == null || r.score === '') && (total === 0 || total == null) && (r.status === 'submitted' || r.status === 'pending');
    if (pending || emptyScore) {
      document.getElementById('resultScore').textContent = '✓';
      document.getElementById('resultDetail').textContent = r.message || 'Шумо бо муваффақият супоридед. Лутфан интизор шавед, то баллҳоятон муайян шаванд.';
      const st = document.getElementById('resultStatus');
      if (st) { st.textContent = 'Супорида шуд'; st.className = 'badge'; }
      return;
    }
    const scoreVal = r.score ?? r.percent ?? null;
    document.getElementById('resultScore').textContent = (scoreVal != null && scoreVal !== '' ? scoreVal : '—') + '%';
    document.getElementById('resultDetail').textContent = `Дуруст: ${r.correct ?? 0} аз ${r.total ?? 0} · ҳад: ${r.passScore ?? r.pass_score ?? 70}%` + (r.timedOut ? ' · вақт тамом' : '') + (auto ? ' · худкор' : '');
    const st = document.getElementById('resultStatus');
    if (st) {
      const status = r.status || '';
      st.textContent = status === 'passed' ? 'Гузашт' : status === 'failed' ? 'Нагузашт' : (status || '—');
      st.className = 'badge' + (status === 'passed' ? '' : ' fail');
    }
  }
  async function submitExam(auto) {
    if (!examSession || !currentOlympiad) return;
    stopExamTimers();
    const payload = {};
    const qs = examSession.questions || currentOlympiad.questions || [];
    qs.forEach((q) => {
      const sel = getAnswer(q.id);
      if (sel == null) return;
      if (typeof sel === 'string' && !sel.trim()) return;
      const oi = q.originalIndex != null ? q.originalIndex : q.id;
      payload[String(oi)] = sel;
      if (q.id != null) payload[String(q.id)] = sel;
    });
    try {
      const data = await api('/api/olympiads/' + currentOlympiad.id + '/exam-submit', {
        method: 'POST', headers: { 'X-Client-Fingerprint': FP },
        body: JSON.stringify({ sessionId: examSession.sessionId, sessionToken: examSession.sessionToken, answers: payload }),
      });
      showResult(data || {}, auto);
      examSession = null;
    } catch (err) {
      const msg = document.getElementById('examMsg');
      if (msg) { msg.textContent = err.message; msg.classList.remove('hidden'); msg.classList.add('error'); }
      else alert(err.message);
    }
  }
  document.getElementById('submitExamBtn')?.addEventListener('click', async () => {
    if (!examSession || !currentOlympiad) return;
    const total = (currentOlympiad.questions || []).length;
    const answered = (currentOlympiad.questions || []).filter((q) => isAnswered(q.id)).length;
    if (answered < total) { if (!confirm('Баъзе саволҳо ҷавоб надоранд. Ба ҳар ҳол супоред?')) return; }
    await submitExam(false);
  });
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  if (student && student.id) showApp();
})();
