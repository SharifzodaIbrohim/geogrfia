(() => {
  const API = '';
  const STUDENT_KEY = 'geo_student';
  const FP = (() => {
    try {
      let f = localStorage.getItem('geo_fp');
      if (!f) { f = 'fp_' + Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem('geo_fp', f); }
      return f;
    } catch (_) { return 'fp_anon'; }
  })();
  let student = null;
  try { student = JSON.parse(localStorage.getItem(STUDENT_KEY) || 'null'); } catch (_) {}
  const answers = new Map();
  let examSession = null, currentOlympiad = null, currentQIndex = 0, examEndsAt = null, timerIv = null, autosaveIv = null;
  const LETTERS = 'ABCD';
  const loginView = document.getElementById('loginView');
  const appView = document.getElementById('appView');
  const listView = document.getElementById('listView');
  const examView = document.getElementById('examView');
  const resultView = document.getElementById('resultView');
  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (student && student.id) headers['X-Student-Id'] = String(student.id);
    const res = await fetch(API + path, Object.assign({}, opts, { headers }));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.message || ('HTTP ' + res.status));
    return data;
  }
  function showApp() {
    loginView?.classList.add('hidden');
    appView?.classList.remove('hidden');
    document.getElementById('studentName').textContent = student.fullName || student.name || student.id;
    document.getElementById('studentMeta').textContent = [student.className || student.class, student.school].filter(Boolean).join(' · ');
    loadLists();
  }
  document.getElementById('studentLoginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const err = document.getElementById('loginError');
    err?.classList.add('hidden');
    try {
      const id = (document.getElementById('studentIdInput')?.value || '').trim();
      if (!id) throw new Error('ID-ро ворид кунед');
      const data = await api('/api/student/login', { method: 'POST', body: JSON.stringify({ studentId: id, id }) });
      student = data.student || data;
      if (!student.id && student.studentId) student.id = student.studentId;
      if (!student.id) student.id = id;
      localStorage.setItem(STUDENT_KEY, JSON.stringify(student));
      showApp();
    } catch (ex) {
      if (err) { err.textContent = ex.message; err.classList.remove('hidden'); }
    }
  });
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem(STUDENT_KEY); student = null; location.reload();
  });
  function card(o, isQuiz) {
    const title = o.title || o.name || 'Бе ном';
    const id = o.id || o.olympiadId;
    return `<div class="oly-card" data-id="${id}"><h3>${esc(title)}</h3><p class="muted">${esc(o.description || '')}</p><button type="button" class="btn primary start-btn" data-id="${id}" data-quiz="${isQuiz ? 1 : 0}">Оғоз</button></div>`;
  }
  async function loadLists() {
    try {
      let olympiads = [], quizzes = [];
      try {
        const d = await api('/api/student/olympiads?studentId=' + encodeURIComponent(student.id));
        olympiads = d.olympiads || d.items || [];
      } catch (_) {
        try {
          const d = await api('/api/olympiads/active?studentId=' + encodeURIComponent(student.id));
          olympiads = d.olympiads || d.items || d || [];
        } catch (__) {}
      }
      if (!Array.isArray(olympiads)) olympiads = [];
      const olyBox = document.getElementById('olympiadList');
      const quizBox = document.getElementById('quizList');
      const emptyOly = document.getElementById('emptyOly');
      const emptyQuiz = document.getElementById('emptyQuiz');
      if (olyBox) { olyBox.innerHTML = olympiads.map((o) => card(o, false)).join('') || ''; emptyOly?.classList.toggle('hidden', olympiads.length > 0); }
      if (quizBox) { quizBox.innerHTML = quizzes.map((o) => card(o, true)).join('') || ''; emptyQuiz?.classList.toggle('hidden', quizzes.length > 0); }
      document.querySelectorAll('.start-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = btn.dataset.id;
          const oly = olympiads.find((x) => String(x.id) === String(id)) || { id, title: 'Олимпиада' };
          startExam(oly);
        });
      });
    } catch (ex) {
      console.error(ex);
    }
  }
  function answerKey(qid) { const num = Number(qid); return Number.isNaN(num) ? qid : num; }
  function setAnswer(qid, val) { answers.set(answerKey(qid), val); answers.set(String(qid), val); }
  function getAnswer(qid) {
    if (answers.has(qid)) return answers.get(qid);
    if (answers.has(String(qid))) return answers.get(String(qid));
    const num = Number(qid);
    if (!Number.isNaN(num) && answers.has(num)) return answers.get(num);
    return undefined;
  }
  function isAnswered(qid) {
    const v = getAnswer(qid);
    if (v == null) return false;
    if (typeof v === 'string' && !v.trim()) return false;
    return true;
  }
  function packAnswer(q, sel) {
    if (sel == null) return null;
    if (typeof sel === 'object' && !Array.isArray(sel)) return sel;
    if (typeof sel === 'number') {
      const opts = q.options || [];
      const t = opts[sel] != null ? (typeof opts[sel] === 'object' ? (opts[sel].text || opts[sel].label || '') : String(opts[sel])) : '';
      return { i: sel, t: String(t) };
    }
    if (typeof sel === 'string') return { t: sel };
    return sel;
  }
  function stopExamTimers() { if (timerIv) clearInterval(timerIv); if (autosaveIv) clearInterval(autosaveIv); timerIv = autosaveIv = null; }
  function tickExamTimer() {
    const el = document.getElementById('examTimer');
    if (!el) return;
    if (!examEndsAt) { el.textContent = '—'; return; }
    const left = Math.max(0, examEndsAt - Date.now());
    const m = Math.floor(left / 60000), s = Math.floor((left % 60000) / 1000);
    el.textContent = m + ':' + String(s).padStart(2, '0');
    if (left <= 0) submitExam(true);
  }
  async function doAutosave() {
    if (!examSession || !currentOlympiad) return;
    const payload = {};
    (examSession.questions || []).forEach((q) => {
      const sel = getAnswer(q.id);
      if (sel == null) return;
      const packed = packAnswer(q, sel);
      if (packed != null) {
        payload[String(q.id)] = packed;
        if (q.originalIndex != null) payload[String(q.originalIndex)] = packed;
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
      if (data.expiresAt) examEndsAt = new Date(data.expiresAt).getTime();
      else if (data.remainingSec != null) examEndsAt = Date.now() + Number(data.remainingSec) * 1000;
      else examEndsAt = null;
      stopExamTimers();
      timerIv = setInterval(tickExamTimer, 1000); tickExamTimer();
      autosaveIv = setInterval(doAutosave, 15000);
      renderQuestion();
    } catch (err) {
      alert(err.message || 'Оғоз нашуд');
    }
  }
  function renderDots() {
    const qs = examSession?.questions || [];
    const box = document.getElementById('examDots');
    if (!box) return;
    box.innerHTML = qs.map((q, i) => {
      const done = isAnswered(q.id);
      const cur = i === currentQIndex;
      return '<button type="button" class="exam-dot' + (cur ? ' current' : '') + (done ? ' done' : '') + '" data-i="' + i + '">' + (i + 1) + '</button>';
    }).join('');
    box.querySelectorAll('.exam-dot').forEach((b) => b.addEventListener('click', () => { currentQIndex = Number(b.dataset.i); renderQuestion(); }));
  }
  function renderQuestion() {
    const qs = examSession?.questions || [];
    const q = qs[currentQIndex];
    if (!q) return;
    const pane = document.getElementById('examQuestionPane');
    if (!pane) return;
    const qid = String(q.id);
    const selected = getAnswer(q.id);
    let body = '';
    const qtype = String(q.type || 'single').toLowerCase();
    if (qtype === 'short' || qtype === 'text' || qtype === 'number' || qtype === 'numeric' || qtype === 'open') {
      const val = selected != null ? String(selected) : '';
      body = '<input type="text" class="exam-text-input" id="examTextInput" value="' + esc(val) + '" placeholder="Ҷавоб..." />';
    } else if (qtype === 'matching' || qtype === 'match') {
      const left = q.left || [];
      const right = q.right || [];
      const cur = (selected && typeof selected === 'object') ? selected : {};
      body = '<div class="exam-match">' + left.map((L, li) => {
        const sel = cur[String(li)] != null ? String(cur[String(li)]) : '';
        return '<div class="exam-match-row"><span>' + esc(L) + '</span><select data-left="' + li + '" class="match-select"><option value="">—</option>' +
          right.map((r, ri) => '<option value="' + ri + '"' + (sel === String(ri) ? ' selected' : '') + '>' + esc((LETTERS[ri] || (ri + 1)) + '. ' + r) + '</option>').join('') +
          '</select></div>';
      }).join('') + '</div>';
    } else {
      const opts = q.options || [];
      body = '<div class="exam-opts" role="listbox">' + opts.map((opt, oi) => {
        const lab = typeof opt === 'object' ? (opt.text || opt.label || '') : String(opt);
        return '<button type="button" class="exam-opt-btn' + (selected === oi ? ' selected' : '') + '" data-oi="' + oi + '" data-qid="' + esc(qid) + '"><span class="exam-opt-letter">' + (LETTERS[oi] || (oi + 1)) + '</span><span class="exam-opt-label">' + esc(lab) + '</span></button>';
      }).join('') + '</div>';
    }
    pane.innerHTML = '<div class="exam-q"><div class="exam-q-num">Савол ' + (currentQIndex + 1) + ' / ' + qs.length + '</div><div class="exam-q-text">' + esc(q.text || '') + '</div>' + body + '</div>';
    const inp = document.getElementById('examTextInput');
    if (inp) {
      const save = () => setAnswer(qid, inp.value);
      inp.addEventListener('input', save);
      inp.addEventListener('change', save);
    }
    pane.querySelectorAll('.match-select').forEach((sel) => {
      sel.addEventListener('change', () => {
        const map = Object.assign({}, getAnswer(qid) && typeof getAnswer(qid) === 'object' ? getAnswer(qid) : {});
        map[String(sel.dataset.left)] = sel.value;
        setAnswer(qid, map);
        renderDots();
      });
    });
    pane.querySelectorAll('.exam-opt-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        setAnswer(btn.dataset.qid, Number(btn.dataset.oi));
        pane.querySelectorAll('.exam-opt-btn').forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
        renderDots();
      });
    });
    const prev = document.getElementById('examPrevBtn');
    const next = document.getElementById('examNextBtn');
    if (prev) prev.disabled = currentQIndex <= 0;
    if (next) next.disabled = currentQIndex >= qs.length - 1;
    const prog = document.getElementById('examProgress');
    if (prog) prog.textContent = 'Савол ' + (currentQIndex + 1) + ' / ' + qs.length;
    renderDots();
  }
  document.getElementById('examPrevBtn')?.addEventListener('click', () => { if (currentQIndex > 0) { currentQIndex--; renderQuestion(); } });
  document.getElementById('examNextBtn')?.addEventListener('click', () => {
    const qs = examSession?.questions || [];
    if (currentQIndex < qs.length - 1) { currentQIndex++; renderQuestion(); }
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
      document.getElementById('resultDetail').textContent = r.message || 'Шумо бо муваффақият супоридед.';
      const st = document.getElementById('resultStatus');
      if (st) { st.textContent = 'Супорида шуд'; st.className = 'badge'; }
      return;
    }
    const scoreVal = r.score ?? r.percent ?? null;
    document.getElementById('resultScore').textContent = (scoreVal != null && scoreVal !== '' ? scoreVal : '—') + '%';
    document.getElementById('resultDetail').textContent = 'Дуруст: ' + (r.correct ?? 0) + ' аз ' + (r.total ?? 0) + ' · ҳад: ' + (r.passScore ?? r.pass_score ?? 70) + '%' + (r.timedOut ? ' · вақт тамом' : '') + (auto ? ' · худкор' : '');
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
      const packed = packAnswer(q, sel);
      if (packed == null) return;
      payload[String(q.id)] = packed;
      if (q.originalIndex != null) payload[String(q.originalIndex)] = packed;
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
    const total = (examSession.questions || []).length;
    const answered = (examSession.questions || []).filter((q) => isAnswered(q.id)).length;
    if (answered < total) { if (!confirm('Баъзе саволҳо ҷавоб надоранд. Ба ҳар ҳол супоред?')) return; }
    await submitExam(false);
  });
  document.getElementById('backToListBtn')?.addEventListener('click', () => {
    resultView.classList.add('hidden'); listView.classList.remove('hidden'); loadLists();
  });
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&', '<': '<', '>': '>', '"': '"', "'": '&#39;' }[c]));
  }
  if (student && student.id) showApp();
})();
