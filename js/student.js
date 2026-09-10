// Student portal — olympiad UI (aligned with student.html IDs)
(function () {
  'use strict';

  const API = '';
  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function t(key, params) {
    var fallback = {
      previous: '← Пештар',
      next: 'Баъдӣ →',
      submitExam: 'Супоридан',
      logout: 'Баромадан',
      back: 'Бозгашт',
      startExam: 'Оғоз',
      statusParticipated: 'Иштирок кардед',
      questionsCount: 'Саволҳо',
      minutes: 'дақ',
      noLimit: 'Бе маҳдудият',
      timeUp: 'Вақт тамом шуд.',
      yourScore: 'Холи шумо',
      submitted: 'Супорида шуд',
      leaveExam: 'Аз имтиҳон баромадан?',
      noQuestions: 'Саволҳо ёфт нашуданд.',
      questionLabel: 'Савол',
      question: 'Савол',
      questionXofY: 'Савол {n} / {total}'
    };
    var s = null;
    try {
      if (window.GeoI18n && typeof window.GeoI18n.t === 'function') {
        s = window.GeoI18n.t(key, params);
      } else if (typeof window.t === 'function' && window.t !== t) {
        s = window.t(key, params);
      }
    } catch (e) { s = null; }
    // GeoI18n returns the key itself when missing — use local fallback
    if (s == null || s === '' || s === key) {
      s = fallback[key] != null ? fallback[key] : key;
    }
    if (params && typeof s === 'string') {
      Object.keys(params).forEach(function (k) {
        s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), String(params[k]));
      });
    }
    return s;
  }

  function applyStaticI18n() {
    var map = [
      ['examPrevBtn', 'previous'],
      ['examNextBtn', 'next'],
      ['submitExamBtn', 'submitExam'],
      ['logoutBtn', 'logout'],
      ['backToListBtn', 'back']
    ];
    map.forEach(function (pair) {
      var el = $(pair[0]);
      if (el) el.textContent = t(pair[1]);
    });
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (!key) return;
      var val = t(key);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = val;
      else el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
  }

  var student = null;
  var exam = null;
  var timerId = null;
  var autosaveId = null;

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function show(el, on) {
    if (!el) return;
    el.classList.toggle('hidden', !on);
  }

  async function api(path, opts) {
    var r = await fetch(API + path, Object.assign({
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin'
    }, opts || {}));
    var data = null;
    try { data = await r.json(); } catch (e) { data = {}; }
    if (!r.ok) {
      var err = new Error((data && (data.error || data.message)) || ('HTTP ' + r.status));
      err.status = r.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function fmtTime(sec) {
    if (sec == null || sec < 0) return '—';
    sec = Math.floor(sec);
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }

  function saveLocalStudent(s) {
    try { localStorage.setItem('geografia_student', JSON.stringify(s)); } catch (e) {}
  }
  function loadLocalStudent() {
    try { return JSON.parse(localStorage.getItem('geografia_student') || 'null'); } catch (e) { return null; }
  }
  function clearLocalStudent() {
    try { localStorage.removeItem('geografia_student'); } catch (e) {}
  }

  function studentId() {
    if (!student) return '';
    return String(student.id || student.studentId || student.code || student.student_code || '').trim();
  }

  function setStudentHeader() {
    var nameEl = $('studentName');
    var metaEl = $('studentMeta');
    if (!student) return;
    var name = student.fullName || student.name || studentId() || '—';
    if (nameEl) nameEl.textContent = name;
    if (metaEl) {
      var bits = [];
      if (student.className || student.class_name) bits.push(student.className || student.class_name);
      if (student.school || student.school_name) bits.push(student.school || student.school_name);
      metaEl.textContent = bits.length ? (' · ' + bits.join(' · ')) : '';
    }
  }

  async function doLogin(id) {
    var data = await api('/api/student/login', {
      method: 'POST',
      body: JSON.stringify({ studentId: id, id: id, code: id })
    });
    student = data.student || data;
    if (!student.id && !student.studentId && !student.code) student.id = id;
    saveLocalStudent(student);
    return student;
  }

  function logout() {
    student = null;
    exam = null;
    clearLocalStudent();
    stopTimers();
    show($('loginView'), true);
    show($('appView'), false);
    show($('listView'), true);
    show($('examView'), false);
    show($('resultView'), false);
  }

  function stopTimers() {
    if (timerId) { clearInterval(timerId); timerId = null; }
    if (autosaveId) { clearInterval(autosaveId); autosaveId = null; }
  }

  function startTimers() {
    stopTimers();
    if (!exam) return;
    var el = $('examTimer');
    if (exam.noTimeLimit) {
      if (el) el.textContent = t('noLimit');
    } else {
      if (el) el.textContent = fmtTime(exam.remainingSec);
      timerId = setInterval(function () {
        if (!exam || exam.noTimeLimit) return;
        exam.remainingSec = Math.max(0, (exam.remainingSec || 0) - 1);
        if (el) el.textContent = fmtTime(exam.remainingSec);
        if (exam.remainingSec <= 0) {
          stopTimers();
          submitExam(true);
        }
      }, 1000);
    }
    autosaveId = setInterval(function () { autosave(true); }, 15000);
  }

  function updateProgress() {
    var prog = $('examProgress');
    if (!prog) return;
    var total = (exam && exam.questions) ? exam.questions.length : 0;
    var cur = total ? ((exam.idx || 0) + 1) : 0;
    var label = t('questionXofY', { n: cur, total: total });
    if (!label || label === 'questionXofY' || label.indexOf('{') >= 0) {
      label = 'Савол ' + cur + ' / ' + total;
    }
    prog.textContent = label;
  }

  function renderEventCards(box, list, emptyEl, kindLabel) {
    if (!box) return;
    if (!list || !list.length) {
      box.innerHTML = '';
      show(emptyEl, true);
      return;
    }
    show(emptyEl, false);
    box.innerHTML = list.map(function (o) {
      var id = o.id;
      var title = esc(o.title || o.name || kindLabel);
      var nq = o.questionCount || (o.questions && o.questions.length) || '?';
      var dur = o.durationMin != null ? o.durationMin
        : (o.durationSec != null ? Math.round(Number(o.durationSec) / 60) : o.duration);
      var durTxt = (dur === 0 || dur === '0') ? t('noLimit') : (dur ? (dur + ' ' + t('minutes')) : '');
      var done = o.alreadySubmitted || o.finished;
      var locked = o.accessAllowed === false || o.windowStatus === 'locked' || o.windowStatus === 'not_started' || o.windowStatus === 'ended';
      var btn;
      if (done) {
        btn = '<button class="btn" disabled>' + t('statusParticipated') + '</button>';
      } else if (locked && o.isOpen === false) {
        btn = '<button class="btn" disabled>' + esc(o.windowStatus || 'locked') + '</button>';
      } else {
        btn = '<button class="btn primary" data-start="' + esc(id) + '">' + t('startExam') + '</button>';
      }
      return (
        '<div class="card event-card" data-id="' + esc(id) + '">' +
          '<div class="card-title">' + title + '</div>' +
          '<div class="muted">' + t('questionsCount') + ': ' + nq + (durTxt ? ' · ' + durTxt : '') + '</div>' +
          '<div class="card-actions">' + btn + '</div>' +
        '</div>'
      );
    }).join('');
    box.querySelectorAll('[data-start]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-start');
        var card = btn.closest ? btn.closest('.event-card') : null;
        var listTitle = card ? ((card.querySelector('.card-title') || {}).textContent || '') : '';
        startExam(id, listTitle);
      });
    });
  }

  async function loadList() {
    var sid = studentId();
    var data = null;
    try {
      data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(sid || ''));
    } catch (e) {
      try {
        var act = await api('/api/olympiads/active');
        data = { olympiads: act.olympiads || act.items || [], quizzes: act.quizzes || [] };
      } catch (e2) {
        data = { olympiads: [], quizzes: [] };
      }
    }
    var oly = data.olympiads || data.items || [];
    var quizzes = data.quizzes || [];
    if (!quizzes.length) {
      quizzes = oly.filter(function (o) {
        var ty = String(o.type || '').toLowerCase();
        return ty === 'quiz' || ty === 'викторина';
      });
    }
    var pureOly = oly.filter(function (o) {
      var ty = String(o.type || '').toLowerCase();
      return ty !== 'quiz' && ty !== 'викторина';
    });
    renderEventCards($('olympiadList'), pureOly, $('emptyOly'), 'Олимпиада');
    renderEventCards($('quizList'), quizzes, $('emptyQuiz'), 'Викторина');
  }

  async function startExam(olympiadId, listTitle) {
    var sid = studentId();
    if (!sid) {
      alert('Student ID лозим аст.');
      return;
    }
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(olympiadId) + '/start', {
        method: 'POST',
        body: JSON.stringify({ studentId: sid, id: sid, code: sid })
      });
      var questions = data.questions || data.items || [];
      if (!Array.isArray(questions) || !questions.length) {
        alert(t('noQuestions'));
        return;
      }
      questions = questions.map(function (q, i) {
        if (!q || typeof q !== 'object') return { id: 'q' + i, text: String(q), type: 'single', options: [] };
        var opts = (q.options || q.choices || []).map(function (opt) {
          if (typeof opt === 'string') return opt;
          if (opt && typeof opt === 'object') return opt.text || opt.label || opt.value || '';
          return String(opt == null ? '' : opt);
        });
        return {
          id: q.id != null ? String(q.id) : ('q' + i),
          text: q.text || q.question || q.title || '',
          type: String(q.type || 'single').toLowerCase(),
          options: opts,
          pairs: q.pairs || q.matching || null
        };
      });
      var durationMin = data.durationMin != null ? Number(data.durationMin)
        : (data.durationSec != null ? Math.round(Number(data.durationSec) / 60) : null);
      var noTimeLimit = durationMin === 0;
      var remaining = data.remainingSec;
      if (!noTimeLimit && remaining == null && durationMin > 0) remaining = durationMin * 60;
      if (!noTimeLimit && remaining == null) remaining = 60 * 60;
      if (noTimeLimit) remaining = null;

      exam = {
        olympiadId: olympiadId,
        attemptId: data.attemptId || data.id,
        sessionToken: data.sessionToken || data.token || '',
        title: data.title || data.olympiadTitle || listTitle || '',
        questions: questions,
        remainingSec: remaining,
        noTimeLimit: noTimeLimit,
        idx: 0,
        answers: data.answers && typeof data.answers === 'object' ? data.answers : {}
      };

      var titleEl = $('examTitle');
      if (titleEl) titleEl.textContent = exam.title || '—';

      show($('listView'), false);
      show($('resultView'), false);
      show($('examView'), true);
      renderQuestion();
      startTimers();
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  function renderQuestion() {
    if (!exam) return;
    var questions = exam.questions || [];
    var box = $('examQuestionPane') || $('examQuestion');
    if (!box) {
      console.error('[student] missing #examQuestionPane');
      return;
    }
    if (!questions.length) {
      box.innerHTML = '<p class="muted">' + esc(t('noQuestions')) + '</p>';
      updateProgress();
      return;
    }
    if (exam.idx < 0) exam.idx = 0;
    if (exam.idx >= questions.length) exam.idx = questions.length - 1;
    var q = questions[exam.idx];
    if (!q) {
      box.innerHTML = '<p class="muted">' + esc(t('noQuestions')) + '</p>';
      updateProgress();
      return;
    }

    var qtype = String(q.type || 'single').toLowerCase();
    var qWord = t('question');
    if (!qWord || qWord === 'question' || qWord === 'questionLabel') qWord = 'Савол';
    var html = '<div class="exam-q-num">' + esc(qWord) + ' ' + (exam.idx + 1) + '</div>';
    html += '<div class="exam-q-text exam-q">' + esc(q.text || '') + '</div>';

    if (qtype === 'short' || qtype === 'text') {
      var cur = exam.answers[q.id] != null ? exam.answers[q.id] : '';
      html += '<textarea class="exam-text-input exam-text" rows="4" placeholder="Ҷавоби худро нависед…">' +
        esc(cur) + '</textarea>';
    } else {
      var opts = q.options || [];
      if (!opts.length) {
        html += '<p class="muted">Вариантҳо нестанд.</p>';
      } else {
        html += '<div class="exam-opts">';
        opts.forEach(function (opt, i) {
          var letter = LETTERS[i] || String(i + 1);
          var val = typeof opt === 'string' ? opt : String(opt == null ? '' : opt);
          var selected = exam.answers[q.id] === i || exam.answers[q.id] === String(i);
          html += '<label class="exam-opt' + (selected ? ' selected' : '') + '">' +
            '<input type="radio" name="ans" value="' + i + '"' + (selected ? ' checked' : '') + ' />' +
            '<span class="opt-letter">' + letter + '</span>' +
            '<span class="exam-opt-label">' + esc(val) + '</span></label>';
        });
        html += '</div>';
      }
    }

    box.innerHTML = html;
    box.querySelectorAll('input[name=ans]').forEach(function (inp) {
      inp.addEventListener('change', function () {
        exam.answers[q.id] = Number(inp.value);
        box.querySelectorAll('.exam-opt').forEach(function (lab) { lab.classList.remove('selected'); });
        var lab = inp.closest ? inp.closest('.exam-opt') : null;
        if (lab) lab.classList.add('selected');
        updateDots();
      });
    });
    var ta = box.querySelector('textarea.exam-text, textarea.exam-text-input');
    if (ta) {
      ta.addEventListener('input', function () {
        exam.answers[q.id] = ta.value;
        updateDots();
      });
    }
    updateDots();
    updateProgress();
  }

  function updateDots() {
    if (!exam) return;
    var dots = $('examDots');
    if (!dots) return;
    dots.innerHTML = exam.questions.map(function (qq, i) {
      var answered = exam.answers[qq.id] != null && exam.answers[qq.id] !== '';
      var cls = 'dot';
      if (i === exam.idx) cls += ' active';
      if (answered) cls += ' done answered';
      return '<span class="' + cls + '" data-i="' + i + '" title="' + (i + 1) + '"></span>';
    }).join('');
    dots.querySelectorAll('[data-i]').forEach(function (d) {
      d.addEventListener('click', function () {
        exam.idx = Number(d.getAttribute('data-i'));
        renderQuestion();
      });
    });
  }

  async function autosave(silent) {
    if (!exam) return;
    var sid = studentId();
    try {
      await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/autosave', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: exam.attemptId,
          sessionToken: exam.sessionToken,
          studentId: sid,
          answers: exam.answers
        })
      });
    } catch (e) {
      if (!silent) console.warn('autosave', e);
    }
  }

  async function submitExam(auto) {
    if (!exam) return;
    stopTimers();
    var sid = studentId();
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/exam-submit', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: exam.attemptId,
          sessionToken: exam.sessionToken,
          studentId: sid,
          answers: exam.answers,
          timedOut: !!auto
        })
      });
      var score = data.score != null ? data.score : data.percent;
      var msg = (auto ? (t('timeUp') + ' ') : '') +
        (score != null ? (t('yourScore') + ': ' + score + '%') : t('submitted'));
      var scoreEl = $('resultScore');
      var detailEl = $('resultDetail');
      var statusEl = $('resultStatus');
      if (scoreEl) scoreEl.textContent = (score != null ? score : '—') + (score != null ? '%' : '');
      if (detailEl) detailEl.textContent = msg;
      if (statusEl) statusEl.textContent = data.passed ? 'Гузашт' : (data.status || (auto ? 'timeout' : 'submitted'));
      exam = null;
      show($('examView'), false);
      if ($('resultView')) {
        show($('resultView'), true);
        show($('listView'), false);
      } else {
        alert(msg);
        show($('listView'), true);
        loadList();
      }
    } catch (e) {
      alert(e.message || String(e));
      startTimers();
    }
  }

  function bindUI() {
    var loginForm = $('studentLoginForm');
    if (loginForm) {
      loginForm.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var inp = $('studentIdInput') || $('studentLogin');
        var id = (inp && inp.value || '').trim();
        if (!id) return;
        var err = $('loginError');
        if (err) { err.textContent = ''; show(err, false); }
        try {
          await doLogin(id);
          show($('loginView'), false);
          show($('appView'), true);
          setStudentHeader();
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
      if (!exam || !exam.questions.length) return;
      exam.idx = Math.max(0, exam.idx - 1);
      renderQuestion();
    });
    var next = $('examNextBtn');
    if (next) next.addEventListener('click', function () {
      if (!exam || !exam.questions.length) return;
      exam.idx = Math.min(exam.questions.length - 1, exam.idx + 1);
      renderQuestion();
    });
    var sub = $('submitExamBtn');
    if (sub) sub.addEventListener('click', function () { submitExam(false); });
    var back = $('backToListBtn');
    if (back) back.addEventListener('click', function () {
      show($('resultView'), false);
      show($('examView'), false);
      show($('listView'), true);
      loadList();
    });
  }

  function init() {
    bindUI();
    applyStaticI18n();
    var saved = loadLocalStudent();
    if (saved && (saved.id || saved.studentId || saved.code || saved.student_code)) {
      student = saved;
      show($('loginView'), false);
      show($('appView'), true);
      setStudentHeader();
      show($('listView'), true);
      show($('examView'), false);
      show($('resultView'), false);
      loadList();
    } else {
      show($('loginView'), true);
      show($('appView'), false);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
