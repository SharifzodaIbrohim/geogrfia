/* student portal — login, olympiad list, exam, matching support */
(function () {
  'use strict';

  var LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
  var exam = null;
  var timerId = null;

  var I18N = {
    tj: {
      previous: '\u2190 \u049a\u0430\u0431\u043b\u04e3', next: '\u0411\u0430\u044a\u0434\u04e3 \u2192', submitExam: '\u0421\u0443\u043f\u043e\u0440\u0438\u0434\u0430\u043d', logout: '\u0411\u0430\u0440\u043e\u043c\u0430\u0434\u0430\u043d',
      back: '\u0411\u043e\u0437\u0433\u0430\u0448\u0442', startExam: '\u041e\u0493\u043e\u0437', submitted: '\u0421\u0443\u043f\u043e\u0440\u0438\u0434\u0430 \u0448\u0443\u0434',
      timeUp: '\u0412\u0430\u049b\u0442 \u0442\u0430\u043c\u043e\u043c \u0448\u0443\u0434.', yourScore: '\u0425\u043e\u043b\u0438 \u0448\u0443\u043c\u043e', pendingReview: '\u0428\u0443\u043c\u043e \u0431\u043e \u043c\u0443\u0432\u0430\u0444\u0444\u0430\u049b\u0438\u044f\u0442 \u0441\u0443\u043f\u043e\u0440\u0438\u0434\u0435\u0434. \u041d\u0430\u0442\u0438\u04b7\u0430 \u0431\u0430\u044a\u0434\u0442\u0430\u0440 \u0430\u0437 \u04b7\u043e\u043d\u0438\u0431\u0438 \u0430\u0434\u043c\u0438\u043d \u044d\u044a\u043b\u043e\u043d \u043c\u0435\u0448\u0430\u0432\u0430\u0434.',
      timeout: '\u0412\u0430\u049b\u0442 \u0442\u0430\u043c\u043e\u043c', questionLabel: '\u0421\u0430\u0432\u043e\u043b', selectPair: '\u2014 \u0438\u043d\u0442\u0438\u0445\u043e\u0431 \u2014'
    },
    ru: {
      previous: '\u2190 \u041d\u0430\u0437\u0430\u0434', next: '\u0414\u0430\u043b\u0435\u0435 \u2192', submitExam: '\u0421\u0434\u0430\u0442\u044c', logout: '\u0412\u044b\u0439\u0442\u0438',
      back: '\u041d\u0430\u0437\u0430\u0434', startExam: '\u041d\u0430\u0447\u0430\u0442\u044c', submitted: '\u0421\u0434\u0430\u043d\u043e',
      timeUp: '\u0412\u0440\u0435\u043c\u044f \u0432\u044b\u0448\u043b\u043e.', yourScore: '\u0412\u0430\u0448 \u0431\u0430\u043b\u043b', pendingReview: '\u0412\u044b \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u0441\u0434\u0430\u043b\u0438. \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u043f\u043e\u0437\u0436\u0435 \u043e\u0431\u044a\u044f\u0432\u0438\u0442 \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440.',
      timeout: '\u0412\u0440\u0435\u043c\u044f \u0432\u044b\u0448\u043b\u043e', questionLabel: '\u0412\u043e\u043f\u0440\u043e\u0441', selectPair: '\u2014 \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u2014'
    },
    en: {
      previous: '\u2190 Previous', next: 'Next \u2192', submitExam: 'Submit', logout: 'Logout',
      back: 'Back', startExam: 'Start', submitted: 'Submitted',
      timeUp: 'Time is up.', yourScore: 'Your score', pendingReview: 'You submitted successfully. Results will be announced by admin later.',
      timeout: 'Timeout', questionLabel: 'Question', selectPair: '\u2014 select \u2014'
    }
  };

  function lang() {
    try {
      return localStorage.getItem('pfLang') || localStorage.getItem('geo_lang') || 'tj';
    } catch (e) {
      return 'tj';
    }
  }

  function t(key) {
    var L = I18N[lang()] || I18N.tj;
    return (L && L[key]) || (I18N.tj && I18N.tj[key]) || key;
  }

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '\x26amp;')
      .replace(/</g, '\x26lt;')
      .replace(/>/g, '\x26gt;')
      .replace(/"/g, '\x26quot;');
  }

  function show(el, on) {
    if (!el) return;
    if (on) el.classList.remove('hidden');
    else el.classList.add('hidden');
  }

  function studentId() {
    try {
      return localStorage.getItem('geo_student_id') || '';
    } catch (e) {
      return '';
    }
  }

  async function api(path, options) {
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    var tok = '';
    try {
      tok = localStorage.getItem('geo_student_token') || '';
    } catch (e) {}
    if (tok) {
      headers['X-Student-Token'] = tok;
      headers['Authorization'] = 'Bearer ' + tok;
    }
    var sid = studentId();
    if (sid) headers['X-Student-Id'] = sid;
    var res = await fetch(path, Object.assign({}, options, { headers: headers }));
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.reason || ('HTTP ' + res.status));
    return data;
  }

  function fillStudentHeader() {
    var name = '';
    var meta = '';
    try {
      name = localStorage.getItem('geo_student_name') || '';
      meta = localStorage.getItem('geo_student_meta') || '';
    } catch (e) {}
    var nEl = $('studentName');
    var mEl = $('studentMeta');
    if (nEl) nEl.textContent = name || ('ID ' + studentId());
    if (mEl) mEl.textContent = meta || '';
  }

  function stopTimers() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  function renderQuestion() {
    if (!exam || !exam.questions) return;
    var qs = exam.questions;
    var idx = exam.idx || 0;
    if (idx < 0) idx = 0;
    if (idx >= qs.length) idx = qs.length - 1;
    exam.idx = idx;
    var q = qs[idx];
    var pane = $('examQuestionPane');
    if (!pane || !q) return;
    var prog = $('examProgress');
    if (prog) prog.textContent = t('questionLabel') + ' ' + (idx + 1) + ' / ' + qs.length;

    var html = '<div class="exam-q"><p class="exam-q-text">' + esc(q.text || '') + '</p>';
    var type = (q.type || 'single').toLowerCase();
    var ans = (exam.answers && exam.answers[q.id]) != null ? exam.answers[q.id] : null;

    if (type === 'short' || type === 'text') {
      html += '<input type="text" class="exam-input" data-qid="' + esc(q.id) + '" value="' + esc(ans != null ? ans : '') + '" placeholder="..." />';
    } else if (type === 'matching' || type === 'match') {
      var left = q.leftItems || q.left || [];
      var right = q.rightItems || q.right || [];
      var map = (ans && typeof ans === 'object') ? ans : {};
      html += '<div class="exam-match">';
      left.forEach(function (L, i) {
        var key = String(i);
        html += '<div class="exam-match-row"><span>' + esc(L) + '</span><select data-qid="' + esc(q.id) + '" data-left="' + key + '">';
        html += '<option value="">' + esc(t('selectPair')) + '</option>';
        right.forEach(function (R, j) {
          var sel = map[key] == j || map[key] == String(j) ? ' selected' : '';
          html += '<option value="' + j + '"' + sel + '>' + esc(R) + '</option>';
        });
        html += '</select></div>';
      });
      html += '</div>';
    } else {
      var opts = q.options || [];
      html += '<div class="exam-opts">';
      opts.forEach(function (o, i) {
        var letter = LETTERS[i] || (i + 1);
        var checked = ans === i || ans === String(i) ? ' checked' : '';
        html += '<label class="exam-opt"><input type="radio" name="q' + esc(q.id) + '" value="' + i + '"' + checked + ' data-qid="' + esc(q.id) + '" /> <span>' + letter + '. ' + esc(o) + '</span></label>';
      });
      html += '</div>';
    }
    html += '</div>';
    pane.innerHTML = html;

    pane.querySelectorAll('input[type=radio]').forEach(function (inp) {
      inp.addEventListener('change', function () {
        if (!exam.answers) exam.answers = {};
        exam.answers[inp.dataset.qid] = Number(inp.value);
      });
    });
    pane.querySelectorAll('input.exam-input').forEach(function (inp) {
      inp.addEventListener('input', function () {
        if (!exam.answers) exam.answers = {};
        exam.answers[inp.dataset.qid] = inp.value;
      });
    });
    pane.querySelectorAll('select[data-left]').forEach(function (sel) {
      sel.addEventListener('change', function () {
        if (!exam.answers) exam.answers = {};
        var qid = sel.dataset.qid;
        if (!exam.answers[qid] || typeof exam.answers[qid] !== 'object') exam.answers[qid] = {};
        exam.answers[qid][sel.dataset.left] = sel.value === '' ? null : Number(sel.value);
      });
    });

    var dots = $('examDots');
    if (dots) {
      dots.innerHTML = qs.map(function (_, i) {
        return '<span class="dot' + (i === idx ? ' on' : '') + '"></span>';
      }).join('');
    }
  }

  async function submitExam(auto) {
    if (!exam) return;
    stopTimers();
    if (!auto) {
      if (!window.confirm(lang() === 'ru' ? 'Submit?' : lang() === 'en' ? 'Submit exam?' : 'Submit?')) return;
    }
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/submit', {
        method: 'POST',
        body: JSON.stringify({ studentId: studentId(), attemptId: exam.attemptId, answers: exam.answers })
      });
      var score = data.score != null ? data.score : data.percent;
      var hide = !!(data.hideScore || data.showResultsToStudents === false || data.pendingReview);
      var scoreEl = $('resultScore');
      var detailEl = $('resultDetail');
      var statusEl = $('resultStatus');
      if (hide) {
        if (scoreEl) scoreEl.style.display = 'none';
        if (detailEl) detailEl.textContent = data.message || t('pendingReview');
        if (statusEl) statusEl.textContent = t('submitted');
      } else {
        if (scoreEl) {
          scoreEl.style.display = '';
          scoreEl.textContent = (score != null ? score : '\u2014') + (score != null ? '%' : '');
        }
        if (detailEl) {
          detailEl.textContent = (auto ? (t('timeUp') + ' ') : '') + (score != null ? (t('yourScore') + ': ' + score + '%') : t('submitted'));
        }
        if (statusEl) statusEl.textContent = data.passed ? 'OK' : (auto ? t('timeout') : t('submitted'));
      }
      exam = null;
      show($('examView'), false);
      if ($('resultView')) { show($('resultView'), true); show($('listView'), false); }
      else { alert(hide ? t('submitted') : ((score != null ? score + '%' : t('submitted')))); show($('listView'), true); }
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  async function startExam(olympiadId) {
    stopTimers();
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(olympiadId) + '/start', {
        method: 'POST',
        body: JSON.stringify({ studentId: studentId(), student_id: studentId() })
      });
      var qs = data.questions || (data.exam && data.exam.questions) || data.items || [];
      var rem = data.remainingSec != null ? Number(data.remainingSec)
        : (data.durationSec != null ? Number(data.durationSec)
        : (data.durationMin != null ? Number(data.durationMin) * 60 : 0));
      if (!isFinite(rem) || rem < 0) rem = 0;
      exam = {
        olympiadId: olympiadId,
        attemptId: data.attemptId || data.id || null,
        questions: qs,
        answers: {},
        idx: 0,
        durationSec: rem,
        endsAt: data.endsAt || null
      };
      var title = $('examTitle');
      if (title) title.textContent = data.title || data.name || 'Olympiad';
      show($('listView'), false);
      show($('resultView'), false);
      show($('examView'), true);
      renderQuestion();
      if (rem > 0 || exam.endsAt) {
        var el = $('examTimer');
        function paintTimer(sec) {
          if (!el) return;
          var m = Math.floor(sec / 60);
          var s = sec % 60;
          el.textContent = m + ':' + (s < 10 ? '0' : '') + s;
        }
        if (exam.endsAt || exam.durationSec) {
          var end = exam.endsAt ? new Date(exam.endsAt).getTime() : (Date.now() + exam.durationSec * 1000);
          paintTimer(Math.max(0, Math.floor((end - Date.now()) / 1000)));
          timerId = setInterval(function () {
            var left = Math.max(0, Math.floor((end - Date.now()) / 1000));
            paintTimer(left);
            if (left <= 0) submitExam(true);
          }, 1000);
        }
      } else {
        var tel = $('examTimer');
        if (tel) tel.textContent = '\u2014';
      }
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  async function loadList() {
    try {
      var data = await api('/api/olympiads/active');
      var list = data.olympiads || [];
      var box = $('olympiadList');
      var empty = $('olympiadEmpty');
      if (!box) return;
      if (!list.length) {
        box.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        return;
      }
      if (empty) empty.classList.add('hidden');
      box.innerHTML = list.map(function (o) {
        var done = !!(o.alreadySubmitted || o.finished || o.submitted);
        var btn = done
          ? '<button class="btn" disabled>' + esc(t('submitted')) + '</button>'
          : '<button class="btn primary" data-start="' + esc(o.id) + '">' + esc(t('startExam')) + '</button>';
        return '<article class="card"><h3>' + esc(o.title) + '</h3><p class="muted">' +
          (o.questionCount || 0) + ' · ' + (o.passScore || 70) + '%</p>' + btn + '</article>';
      }).join('');
      box.querySelectorAll('[data-start]').forEach(function (btn) {
        btn.addEventListener('click', function () { startExam(btn.dataset.start); });
      });
    } catch (e) {
      console.error(e);
    }
  }

  function bindNav() {
    var prev = $('examPrevBtn') || $('prevQuestionBtn');
    var next = $('examNextBtn') || $('nextQuestionBtn');
    var sub = $('submitExamBtn');
    if (prev) prev.addEventListener('click', function () {
      if (!exam) return;
      exam.idx = Math.max(0, exam.idx - 1);
      renderQuestion();
    });
    if (next) next.addEventListener('click', function () {
      if (!exam) return;
      exam.idx = Math.min(exam.questions.length - 1, exam.idx + 1);
      renderQuestion();
    });
    if (sub) sub.addEventListener('click', function () { submitExam(false); });
    var back = $('resultBackBtn');
    if (back && !back.dataset.bound) {
      back.dataset.bound = '1';
      back.addEventListener('click', function () {
        show($('resultView'), false);
        show($('examView'), false);
        show($('listView'), true);
        try { loadList(); } catch (e) {}
      });
    }
  }

  function init() {
    bindNav();
    if (studentId()) {
      fillStudentHeader();
      show($('loginView'), false);
      show($('appView') || $('listView'), true);
      loadList();
    }
    var form = $('studentLoginForm');
    if (form) {
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var id = String((($('studentIdInput') || {}).value || '')).trim();
        if (!id) return;
        try {
          var data = await api('/api/student/login', { method: 'POST', body: JSON.stringify({ studentId: id }) });
          localStorage.setItem('geo_student_id', data.studentId || (data.student && data.student.id) || id);
          if (data.token) localStorage.setItem('geo_student_token', data.token);
          try {
            var st = data.student || {};
            localStorage.setItem('geo_student_name', st.fullName || st.name || '');
            localStorage.setItem('geo_student_meta', [st.className || '', st.school || ''].filter(Boolean).join(' \u00b7 '));
          } catch (e0) {}
          fillStudentHeader();
          show($('loginView'), false);
          show($('appView') || $('listView'), true);
          loadList();
        } catch (e) { alert(e.message || String(e)); }
      });
    }
    var lo = $('logoutBtn');
    if (lo) lo.addEventListener('click', function () {
      localStorage.removeItem('geo_student_id');
      localStorage.removeItem('geo_student_token');
      localStorage.removeItem('geo_student_name');
      localStorage.removeItem('geo_student_meta');
      location.reload();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
