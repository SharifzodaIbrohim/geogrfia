// Student portal — compact restore (confirm + hideScore + one-attempt)
(function () {
  'use strict';
  var API = '';
  var LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  var student = null, exam = null, timerId = null, autosaveId = null;

  function t(key) {
    var m = {
      previous: '← Қаблӣ', next: 'Баъдӣ →', submitExam: 'Супоридан', logout: 'Баромадан',
      back: 'Бозгашт', startExam: 'Оғоз', submitted: 'Супорида шуд',
      confirmSubmit: 'Оё шумо мехоҳед супоред? Баъд аз супоридан тағйир дода намешавад.',
      pendingReview: 'Натиҷа баъдтар эълон мешавад.', timeout: 'Вақт тамом шуд',
      yourScore: 'Холи шумо', timeUp: 'Вақт тамом шуд.', noEvents: 'Ҳоло олимпиадаи фаъол нест.',
      questionLabel: 'Савол'
    };
    try {
      if (window.GeoI18n && typeof window.GeoI18n.t === 'function') {
        var s = window.GeoI18n.t(key);
        if (s && s !== key) return s;
      }
    } catch (e) {}
    return m[key] || key;
  }

  function $(id) { return document.getElementById(id); }
  function show(el, on) { if (el) el.classList.toggle('hidden', !on); }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function studentId() {
    if (!student) return '';
    return String(student.id || student.studentId || student.code || student.student_code || '').trim();
  }
  function fmtTime(sec) {
    if (sec == null || sec < 0) return '—';
    sec = Math.floor(sec);
    var m = Math.floor(sec / 60), s = sec % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }
  function saveLocal(s) { try { localStorage.setItem('geografia_student', JSON.stringify(s)); } catch (e) {} }
  function loadLocal() {
    try { return JSON.parse(localStorage.getItem('geografia_student') || 'null'); } catch (e) { return null; }
  }
  function clearLocal() { try { localStorage.removeItem('geografia_student'); } catch (e) {} }

  async function api(path, opts) {
    opts = opts || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    var sid = studentId();
    if (sid) headers['X-Student-Id'] = sid;
    var r;
    try {
      r = await fetch(API + path, Object.assign({ credentials: 'same-origin', headers: headers }, opts));
    } catch (net) {
      var ne = new Error('Хатои шабака. Пайвастро санҷед ва саҳифаро навсозӣ кунед.');
      ne.status = 0; throw ne;
    }
    var data = {};
    try { data = await r.json(); } catch (e) {}
    if (!r.ok) {
      var err = new Error((data && (data.error || data.message)) || ('HTTP ' + r.status));
      err.status = r.status; err.data = data; throw err;
    }
    return data;
  }

  function setHeader() {
    var nameEl = $('studentName') || $('studentHeader');
    if (!student || !nameEl) return;
    var name = student.fullName || student.name || studentId() || '—';
    var bits = [];
    if (student.className || student.class_name) bits.push(student.className || student.class_name);
    if (student.school || student.school_name) bits.push(student.school || student.school_name);
    nameEl.textContent = bits.length ? (name + ' · ' + bits.join(' · ')) : name;
  }

  async function doLogin(id) {
    var data = await api('/api/student/login', { method: 'POST', body: JSON.stringify({ studentId: id, id: id, code: id }) });
    student = data.student || data;
    saveLocal(student);
    return student;
  }

  function logout() {
    student = null; exam = null; clearLocal();
    stopTimers();
    show($('loginView'), true);
    show($('appView'), false);
  }

  async function loadList() {
    var box = $('olympiadList') || $('eventList');
    var empty = $('olympiadEmpty') || $('eventEmpty');
    if (!box) return;
    box.innerHTML = '';
    try {
      var data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(studentId()));
      var list = (data.olympiads || []).concat(data.quizzes || []);
      if (!list.length) {
        if (empty) { empty.textContent = t('noEvents'); show(empty, true); }
        return;
      }
      show(empty, false);
      list.forEach(function (o) {
        var id = o.id;
        var done = !!(o.alreadySubmitted || o.finished || o.submitted);
        var card = document.createElement('div');
        card.className = 'event-card card';
        var btn;
        if (done) {
          btn = '<span class="badge">' + esc(t('submitted')) + '</span>';
        } else if (o.isOpen !== false) {
          btn = '<button class="btn primary" data-start="' + esc(id) + '">' + esc(t('startExam')) + '</button>';
        } else {
          btn = '<span class="muted">' + esc(o.windowStatus || '—') + '</span>';
        }
        card.innerHTML =
          '<div class="event-title">' + esc(o.title || 'Олимпиада') + '</div>' +
          '<div class="event-meta muted">' + esc((o.questionCount || '?') + ' савол · ' + (o.durationSec ? Math.round(o.durationSec / 60) + ' дақ' : '—')) + '</div>' +
          '<div class="event-actions">' + btn + '</div>';
        box.appendChild(card);
      });
      box.querySelectorAll('[data-start]').forEach(function (b) {
        b.addEventListener('click', function () { startExam(b.getAttribute('data-start')); });
      });
    } catch (e) {
      if (empty) { empty.textContent = e.message || String(e); show(empty, true); }
    }
  }

  function stopTimers() {
    if (timerId) { clearInterval(timerId); timerId = null; }
    if (autosaveId) { clearInterval(autosaveId); autosaveId = null; }
  }

  function startTimers() {
    stopTimers();
    if (!exam) return;
    timerId = setInterval(function () {
      if (!exam) return;
      var left = exam.remainingSec != null ? exam.remainingSec : null;
      if (left == null && exam.expiresAt) {
        left = Math.floor((new Date(exam.expiresAt).getTime() - Date.now()) / 1000);
      }
      if (left != null) {
        exam.remainingSec = left - 1;
        var el = $('examTimer');
        if (el) el.textContent = fmtTime(exam.remainingSec);
        if (exam.remainingSec <= 0) {
          stopTimers();
          submitExam(true);
        }
      }
    }, 1000);
    autosaveId = setInterval(function () { autosave(true); }, 20000);
  }

  async function autosave(silent) {
    if (!exam) return;
    try {
      await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/exam-save', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: exam.attemptId, sessionToken: exam.sessionToken,
          studentId: studentId(), answers: exam.answers || {}
        })
      });
    } catch (e) { if (!silent) console.warn('autosave', e); }
  }

  async function startExam(olympiadId) {
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(olympiadId) + '/start', {
        method: 'POST',
        body: JSON.stringify({ studentId: studentId(), studentCode: studentId() })
      });
      var qs = data.questions || (data.exam && data.exam.questions) || [];
      exam = {
        olympiadId: olympiadId,
        attemptId: data.attemptId || data.sessionId || data.id,
        sessionToken: data.sessionToken,
        questions: qs,
        answers: data.answers || {},
        idx: 0,
        remainingSec: data.remainingSec != null ? data.remainingSec : data.durationSec,
        expiresAt: data.expiresAt,
        title: data.title || ''
      };
      show($('listView'), false);
      show($('resultView'), false);
      show($('examView'), true);
      var titleEl = $('examTitle');
      if (titleEl) titleEl.textContent = exam.title || 'Олимпиада';
      renderQuestion();
      startTimers();
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  function normalizeQ(q, i) {
    if (!q) return { id: String(i), text: '', type: 'single', options: [] };
    var opts = q.options || q.choices || [];
    opts = opts.map(function (o, j) {
      if (typeof o === 'string') return { text: o, letter: LETTERS[j] || String(j) };
      return {
        text: o.text || o.label || o.value || String(o),
        letter: o.letter || LETTERS[j] || String(j),
        id: o.id != null ? o.id : j
      };
    });
    return {
      id: q.id != null ? String(q.id) : String(i),
      text: q.text || q.question || q.title || '',
      type: (q.type || q.qtype || 'single').toLowerCase(),
      options: opts
    };
  }

  function renderQuestion() {
    if (!exam || !exam.questions.length) return;
    var pane = $('examQuestionPane') || $('examQuestion');
    if (!pane) return;
    var q = normalizeQ(exam.questions[exam.idx], exam.idx);
    var prog = $('examProgress');
    if (prog) prog.textContent = t('questionLabel') + ' ' + (exam.idx + 1) + ' / ' + exam.questions.length;
    var html = '<div class="q-text"><strong>' + esc(t('questionLabel') + ' ' + (exam.idx + 1)) + '</strong><p>' + esc(q.text) + '</p></div>';
    var cur = exam.answers[q.id];
    if (q.type === 'single' || q.type === 'choice' || q.type === 'mcq' || !q.type) {
      html += '<div class="exam-options">';
      q.options.forEach(function (opt, j) {
        var val = opt.id != null ? opt.id : j;
        var sel = String(cur) === String(val) || String(cur) === String(j) || cur === opt.text;
        html += '<button type="button" class="exam-opt' + (sel ? ' selected' : '') + '" data-qid="' + esc(q.id) + '" data-val="' + esc(val) + '">' +
          '<span class="opt-letter">' + esc(opt.letter || LETTERS[j]) + '</span> ' + esc(opt.text) + '</button>';
      });
      html += '</div>';
    } else if (q.type === 'short' || q.type === 'text') {
      html += '<input class="exam-input" data-qid="' + esc(q.id) + '" value="' + esc(cur || '') + '" />';
    } else {
      html += '<textarea class="exam-input" data-qid="' + esc(q.id) + '">' + esc(cur || '') + '</textarea>';
    }
    pane.innerHTML = html;
    pane.querySelectorAll('.exam-opt').forEach(function (btn) {
      btn.addEventListener('click', function () {
        exam.answers[btn.getAttribute('data-qid')] = btn.getAttribute('data-val');
        renderQuestion();
      });
    });
    pane.querySelectorAll('.exam-input').forEach(function (inp) {
      inp.addEventListener('change', function () {
        exam.answers[inp.getAttribute('data-qid')] = inp.value;
      });
      inp.addEventListener('input', function () {
        exam.answers[inp.getAttribute('data-qid')] = inp.value;
      });
    });
  }

  async function submitExam(auto) {
    if (!exam) return;
    stopTimers();
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/exam-submit', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: exam.attemptId,
          sessionToken: exam.sessionToken,
          studentId: studentId(),
          answers: exam.answers,
          timedOut: !!auto
        })
      });
      var hide = !!(data.hideScore || data.pendingReview || data.showResultsToStudents === false ||
        (data.result && (data.result.hideScore || data.result.showResultsToStudents === false)));
      var score = data.score != null ? data.score : (data.percent != null ? data.percent : (data.result && data.result.score));
      var scoreEl = $('resultScore');
      var detailEl = $('resultDetail');
      var statusEl = $('resultStatus');
      if (hide) {
        if (scoreEl) { scoreEl.textContent = ''; scoreEl.style.display = 'none'; }
        if (detailEl) detailEl.textContent = t('submitted') + '. ' + (data.message || t('pendingReview'));
        if (statusEl) statusEl.textContent = t('submitted');
      } else {
        if (scoreEl) {
          scoreEl.style.display = '';
          scoreEl.textContent = (score != null ? score : '—') + (score != null ? '%' : '');
        }
        if (detailEl) {
          detailEl.textContent = (auto ? (t('timeUp') + ' ') : '') +
            (score != null ? (t('yourScore') + ': ' + score + '%') : t('submitted'));
        }
        if (statusEl) {
          statusEl.textContent = data.passed ? 'Гузашт' : (auto ? t('timeout') : t('submitted'));
        }
      }
      exam = null;
      show($('examView'), false);
      if ($('resultView')) {
        show($('resultView'), true);
        show($('listView'), false);
      } else {
        alert(hide ? t('submitted') : ((score != null ? score + '%' : t('submitted'))));
        show($('listView'), true);
        loadList();
      }
    } catch (e) {
      alert(e.message || String(e));
      startTimers();
    }
  }

  function bindUI() {
    var form = $('studentLoginForm');
    if (form) {
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var inp = $('studentIdInput') || $('studentLogin') || document.querySelector('[name="studentId"]');
        var id = (inp && inp.value || '').trim();
        var err = $('loginError');
        if (!id) { if (err) { err.textContent = 'ID-ро нависед.'; show(err, true); } return; }
        if (err) { err.textContent = ''; show(err, false); }
        try {
          await doLogin(id);
          show($('loginView'), false);
          show($('appView'), true);
          setHeader();
          show($('listView'), true);
          show($('examView'), false);
          show($('resultView'), false);
          loadList();
        } catch (e) {
          if (err) { err.textContent = e.message || String(e); show(err, true); }
          else alert(e.message || String(e));
        }
      });
    }
    var lo = $('logoutBtn');
    if (lo) lo.addEventListener('click', logout);
    var prev = $('examPrevBtn');
    if (prev) prev.addEventListener('click', function () {
      if (!exam) return;
      exam.idx = Math.max(0, exam.idx - 1);
      renderQuestion();
    });
    var next = $('examNextBtn');
    if (next) next.addEventListener('click', function () {
      if (!exam) return;
      exam.idx = Math.min(exam.questions.length - 1, exam.idx + 1);
      renderQuestion();
    });
    var sub = $('submitExamBtn');
    if (sub) {
      sub.addEventListener('click', function () {
        if (!window.confirm(t('confirmSubmit'))) return;
        submitExam(false);
      });
    }
    var back = $('resultBackBtn') || $('backToListBtn');
    if (back) back.addEventListener('click', function () {
      show($('resultView'), false);
      show($('examView'), false);
      show($('listView'), true);
      loadList();
    });
  }

  function boot() {
    bindUI();
    var saved = loadLocal();
    if (saved && (saved.id || saved.studentId || saved.code)) {
      student = saved;
      show($('loginView'), false);
      show($('appView'), true);
      setHeader();
      show($('listView'), true);
      loadList();
    } else {
      show($('loginView'), true);
      show($('appView'), false);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
