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
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function show(el, on) {
    if (!el) return;
    if (on) el.classList.remove('hidden');
    else el.classList.add('hidden');
  }

  function loadLocalStudent() {
    try {
      var raw = localStorage.getItem('geo_student');
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function saveLocalStudent(st) {
    try { localStorage.setItem('geo_student', JSON.stringify(st)); } catch (e) {}
  }

  function setStudentHeader() {
    var el = $('studentHeader');
    if (!el || !student) return;
    var name = student.fullName || student.name || '';
    var code = student.id || student.studentId || student.code || student.student_code || '';
    var school = student.school || student.schoolName || '';
    var parts = [name, code, school].filter(Boolean);
    el.textContent = parts.join(' · ');
  }

  async function api(path, opts) {
    opts = opts || {};
    var headers = opts.headers || {};
    if (!headers['Content-Type'] && opts.body) headers['Content-Type'] = 'application/json';
    var res = await fetch(API + path, {
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body,
      credentials: 'include'
    });
    var data = null;
    try { data = await res.json(); } catch (e) { data = {}; }
    if (!res.ok) {
      var err = new Error((data && (data.error || data.message)) || ('HTTP ' + res.status));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function stopTimers() {
    if (timerId) { clearInterval(timerId); timerId = null; }
    if (autosaveId) { clearInterval(autosaveId); autosaveId = null; }
  }

  function updateTimerDisplay(sec) {
    var el = $('examTimer');
    if (!el) return;
    if (sec == null || sec < 0) { el.textContent = '—'; return; }
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    el.textContent = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function startTimers(remainingSec) {
    stopTimers();
    var left = remainingSec != null ? Number(remainingSec) : null;
    if (left != null && !isNaN(left)) {
      updateTimerDisplay(Math.max(0, Math.floor(left)));
      timerId = setInterval(function () {
        left -= 1;
        updateTimerDisplay(Math.max(0, Math.floor(left)));
        if (left <= 0) {
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
    prog.textContent = t('questionXofY', { n: cur, total: total });
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
        var card = btn.closest('.event-card');
        var listTitle = card ? (card.querySelector('.card-title') || {}).textContent : '';
        startExam(id, listTitle);
      });
    });
  }

  async function loadList() {
    var olyBox = $('olympiadList');
    var quizBox = $('quizList');
    var emptyO = $('olympiadEmpty');
    var emptyQ = $('quizEmpty');
    try {
      var data = null;
      try {
        data = await api('/api/student/olympiads');
      } catch (e1) {
        try {
          data = await api('/api/olympiads/active');
        } catch (e2) {
          data = { olympiads: [], quizzes: [] };
        }
      }
      var oly = data.olympiads || data.items || data || [];
      if (!Array.isArray(oly)) oly = [];
      var quizzes = data.quizzes || [];
      if (!Array.isArray(quizzes)) quizzes = [];
      // Separate pure olympiad vs quiz-type if mixed
      var olyOnly = oly.filter(function (o) {
        var k = String(o.type || o.kind || 'olympiad').toLowerCase();
        return k !== 'quiz' && k !== 'viktorina';
      });
      var quizFromOly = oly.filter(function (o) {
        var k = String(o.type || o.kind || '').toLowerCase();
        return k === 'quiz' || k === 'viktorina';
      });
      if (!quizzes.length && quizFromOly.length) quizzes = quizFromOly;
      if (!olyOnly.length && oly.length && !quizFromOly.length) olyOnly = oly;
      renderEventCards(olyBox, olyOnly, emptyO, 'Олимпиада');
      renderEventCards(quizBox, quizzes, emptyQ, 'Викторина');
    } catch (err) {
      console.warn('loadList', err);
      if (olyBox) olyBox.innerHTML = '<p class="muted">' + esc(err.message || err) + '</p>';
    }
  }

  async function startExam(olympiadId, listTitle) {
    if (!student) return;
    var code = student.id || student.studentId || student.code || student.student_code;
    try {
      var data = await api('/api/student/olympiads/' + encodeURIComponent(olympiadId) + '/start', {
        method: 'POST',
        body: JSON.stringify({ studentId: code, student_code: code, id: code, code: code })
      });
      var qs = data.questions || data.items || [];
      if (!Array.isArray(qs)) qs = [];
      exam = {
        olympiadId: olympiadId,
        attemptId: data.attemptId || data.sessionId || data.id,
        questions: qs.map(function (q, i) {
          return {
            id: q.id || q.questionId || String(i),
            text: q.text || q.question || '',
            type: q.type || 'single',
            options: q.options || q.choices || [],
            pairs: q.pairs || null
          };
        }),
        answers: data.answers || {},
        idx: 0,
        title: data.title || data.olympiadTitle || listTitle || '',
        remainingSec: data.remainingSec != null ? data.remainingSec : data.timeLimitSec
      };
      var titleEl = $('examTitle');
      if (titleEl) titleEl.textContent = exam.title || 'GEOGRAFIA';
      show($('listView'), false);
      show($('resultView'), false);
      show($('examView'), true);
      renderQuestion();
      startTimers(exam.remainingSec);
    } catch (err) {
      alert(err.message || err);
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
    var html = '<div class="exam-q-num">' + esc(t('questionLabel')) + ' ' + (exam.idx + 1) + '</div>';
    html += '<div class="exam-q-text exam-q">' + esc(q.text || '') + '</div>';

    if (qtype === 'short' || qtype === 'text') {
      var cur = exam.answers[q.id] != null ? exam.answers[q.id] : '';
      html += '<textarea class="exam-text-input exam-text" rows="4" placeholder="Ҷавоби худро нависед…">' +
        esc(cur) + '</textarea>';
    } else if (qtype === 'matching' && q.pairs && q.pairs.length) {
      html += '<div class="exam-match">';
      q.pairs.forEach(function (p, i) {
        var left = typeof p === 'string' ? p : (p.left || p.a || '');
        var rightOpts = (typeof p === 'object' && p.rights) ? p.rights : [];
        html += '<div class="exam-match-row"><span>' + esc(left) + '</span>';
        if (rightOpts.length) {
          html += '<select data-match="' + i + '"><option value="">—</option>';
          rightOpts.forEach(function (r) {
            html += '<option value="' + esc(r) + '">' + esc(r) + '</option>';
          });
          html += '</select>';
        }
        html += '</div>';
      });
      html += '</div>';
    } else {
      var opts = q.options || [];
      html += '<div class="exam-opts">';
      opts.forEach(function (opt, i) {
        var text = typeof opt === 'string' ? opt : (opt.text || opt.label || '');
        var val = typeof opt === 'string' ? opt : (opt.id || opt.value || text);
        var letter = LETTERS[i] || String(i + 1);
        var selected = exam.answers[q.id] === val || exam.answers[q.id] === text;
        html += '<label class="exam-opt' + (selected ? ' selected' : '') + '">' +
          '<input type="radio" name="q_' + esc(q.id) + '" value="' + esc(val) + '"' +
          (selected ? ' checked' : '') + '>' +
          '<span class="exam-opt-letter">' + letter + '</span>' +
          '<span class="exam-opt-text">' + esc(text) + '</span></label>';
      });
      html += '</div>';
    }

    box.innerHTML = html;

    box.querySelectorAll('.exam-opt').forEach(function (lab) {
      lab.addEventListener('click', function () {
        var inp = lab.querySelector('input');
        if (!inp) return;
        inp.checked = true;
        exam.answers[q.id] = inp.value;
        box.querySelectorAll('.exam-opt').forEach(function (x) { x.classList.remove('selected'); });
        lab.classList.add('selected');
      });
    });
    var ta = box.querySelector('textarea');
    if (ta) {
      ta.addEventListener('input', function () {
        exam.answers[q.id] = ta.value;
      });
    }
    box.querySelectorAll('select[data-match]').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var pairs = exam.answers[q.id] || {};
        if (typeof pairs !== 'object') pairs = {};
        pairs[sel.getAttribute('data-match')] = sel.value;
        exam.answers[q.id] = pairs;
      });
    });

    updateProgress();
    var prev = $('examPrevBtn');
    var next = $('examNextBtn');
    if (prev) prev.disabled = exam.idx <= 0;
    if (next) next.disabled = exam.idx >= questions.length - 1;
  }

  async function autosave(silent) {
    if (!exam || !exam.attemptId) return;
    try {
      await api('/api/student/attempts/' + encodeURIComponent(exam.attemptId) + '/save', {
        method: 'POST',
        body: JSON.stringify({ answers: exam.answers })
      });
    } catch (e) {
      if (!silent) console.warn('autosave', e);
    }
  }

  async function submitExam(forced) {
    if (!exam || !exam.attemptId) return;
    if (!forced && !confirm(t('leaveExam').indexOf('?') >= 0 ? t('leaveExam') : (t('leaveExam') + '?'))) return;
    stopTimers();
    try {
      var data = await api('/api/student/attempts/' + encodeURIComponent(exam.attemptId) + '/submit', {
        method: 'POST',
        body: JSON.stringify({ answers: exam.answers })
      });
      show($('examView'), false);
      show($('resultView'), true);
      var scoreEl = $('resultScore');
      if (scoreEl) {
        var sc = data.score != null ? data.score : data.percent;
        scoreEl.textContent = (sc != null ? sc + '%' : '—');
      }
      var msg = $('resultMessage');
      if (msg) msg.textContent = t('submitted');
      exam = null;
    } catch (err) {
      alert(err.message || err);
      startTimers(30);
    }
  }

  function bindUI() {
    $('loginBtn') && $('loginBtn').addEventListener('click', async function () {
      var input = $('studentIdInput');
      var code = (input && input.value || '').trim();
      if (!code) return;
      try {
        var data = await api('/api/student/login', {
          method: 'POST',
          body: JSON.stringify({ studentId: code, id: code, code: code })
        });
        student = data.student || data.user || { id: code, studentId: code, fullName: data.fullName || data.name };
        if (!student.id && !student.studentId) student.id = code;
        saveLocalStudent(student);
        setStudentHeader();
        show($('loginView'), false);
        show($('appView'), true);
        show($('listView'), true);
        show($('examView'), false);
        show($('resultView'), false);
        loadList();
      } catch (err) {
        alert(err.message || err);
      }
    });
    $('logoutBtn') && $('logoutBtn').addEventListener('click', function () {
      student = null;
      exam = null;
      stopTimers();
      try { localStorage.removeItem('geo_student'); } catch (e) {}
      show($('appView'), false);
      show($('loginView'), true);
    });
    $('examPrevBtn') && $('examPrevBtn').addEventListener('click', function () {
      if (!exam || exam.idx <= 0) return;
      exam.idx -= 1;
      renderQuestion();
    });
    $('examNextBtn') && $('examNextBtn').addEventListener('click', function () {
      if (!exam || exam.idx >= (exam.questions || []).length - 1) return;
      exam.idx += 1;
      renderQuestion();
    });
    $('submitExamBtn') && $('submitExamBtn').addEventListener('click', function () {
      submitExam(false);
    });
    $('backToListBtn') && $('backToListBtn').addEventListener('click', function () {
      exam = null;
      stopTimers();
      show($('examView'), false);
      show($('resultView'), false);
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
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
