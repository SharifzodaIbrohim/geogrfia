/* student portal — login, olympiad list, exam, matching support */
(function () {
  'use strict';

  var LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];
  var exam = null;
  var timerId = null;

  var I18N = {
    tj: {
      previous: '← Қаблӣ', next: 'Баъдӣ →', submitExam: 'Супоридан', logout: 'Баромадан',
      back: 'Бозгашт', startExam: 'Оғоз', submitted: 'Супорида шуд',
      timeUp: 'Вақт тамом шуд.', yourScore: 'Холи шумо', pendingReview: 'Шумо бо муваффақият супоридед. Натиҷа баъдтар аз ҷониби админ эълон мешавад.',
      timeout: 'Вақт тамом', questionLabel: 'Савол', selectPair: '— интихоб —'
    },
    ru: {
      previous: '← Назад', next: 'Далее →', submitExam: 'Сдать', logout: 'Выйти',
      back: 'Назад', startExam: 'Начать', submitted: 'Сдано',
      timeUp: 'Время вышло.', yourScore: 'Ваш балл', pendingReview: 'Вы успешно сдали. Результат позже объявит администратор.',
      timeout: 'Время вышло', questionLabel: 'Вопрос', selectPair: '— выбрать —'
    },
    en: {
      previous: '← Previous', next: 'Next →', submitExam: 'Submit', logout: 'Logout',
      back: 'Back', startExam: 'Start', submitted: 'Submitted',
      timeUp: 'Time is up.', yourScore: 'Your score', pendingReview: 'You submitted successfully. Results will be announced by admin later.',
      timeout: 'Timeout', questionLabel: 'Question', selectPair: '— select —'
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
      .replace(/\x26/g, '\x26amp;')
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

  function normalizeQ(q, idx) {
    if (!q || typeof q !== 'object') return { id: String(idx + 1), text: '', type: 'single', options: [] };
    var id = q.id != null ? q.id : (idx + 1);
    var type = (q.type || 'single').toLowerCase();
    if (type === 'choice' || type === 'mcq') type = 'single';
    if (type === 'match') type = 'matching';
    var options = [];
    (q.options || []).forEach(function (o, j) {
      if (o && typeof o === 'object') {
        options.push({ id: o.id != null ? o.id : j, text: o.text || o.label || String(o), letter: o.letter || LETTERS[j] });
      } else {
        options.push({ id: j, text: String(o == null ? '' : o), letter: LETTERS[j] });
      }
    });
    return {
      id: id,
      text: q.text || q.question || '',
      type: type,
      options: options,
      leftItems: q.leftItems || q.left || [],
      rightItems: q.rightItems || q.right || []
    };
  }

  async function api(path, options) {
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    var tok = '';
    try { tok = localStorage.getItem('geo_student_token') || ''; } catch (e) {}
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
    var name = '', meta = '';
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
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  function renderQuestion() {
    if (!exam || !exam.questions || !exam.questions.length) return;
    var pane = $('examQuestionPane') || $('examQuestion');
    if (!pane) return;
    var q = normalizeQ(exam.questions[exam.idx], exam.idx);
    var prog = $('examProgress');
    if (prog) prog.textContent = t('questionLabel') + ' ' + (exam.idx + 1) + ' / ' + exam.questions.length;
    var html = '<div class="exam-q"><p class="exam-q-text">' + esc(q.text) + '</p></div>';
    var cur = exam.answers[q.id];
    if (q.type === 'matching') {
      var map = (cur && typeof cur === 'object' && !Array.isArray(cur)) ? cur : {};
      var left = q.leftItems || [];
      var right = q.rightItems || [];
      html += '<div class="exam-match">';
      left.forEach(function (L, li) {
        var selVal = map[String(li)];
        if (selVal === undefined || selVal === null) selVal = '';
        html += '<div class="exam-match-row">' +
          '<span class="match-left">' + esc(L) + '</span>' +
          '<select class="exam-input match-select" data-qid="' + esc(q.id) + '" data-left="' + li + '">' +
          '<option value="">' + esc(t('selectPair')) + '</option>';
        right.forEach(function (R, ri) {
          var selected = String(selVal) === String(ri);
          html += '<option value="' + ri + '"' + (selected ? ' selected' : '') + '>' + esc(R) + '</option>';
        });
        html += '</select></div>';
      });
      html += '</div>';
    } else if (q.type === 'single' || !q.type) {
      html += '<div class="exam-opts">';
      q.options.forEach(function (opt, j) {
        var val = opt.id != null ? opt.id : j;
        var sel = String(cur) === String(val) || String(cur) === String(j) || cur === opt.text;
        html += '<button type="button" class="exam-opt' + (sel ? ' selected' : '') + '" data-qid="' + esc(q.id) + '" data-val="' + esc(val) + '">' +
          '<span class="opt-letter">' + esc(opt.letter || LETTERS[j]) + '</span> ' + esc(opt.text) + '</button>';
      });
      html += '</div>';
    } else if (q.type === 'short' || q.type === 'text') {
      html += '<input class="exam-input" data-qid="' + esc(q.id) + '" value="' + esc(typeof cur === 'string' || typeof cur === 'number' ? cur : '') + '" />';
    } else {
      html += '<textarea class="exam-input" data-qid="' + esc(q.id) + '">' + esc(typeof cur === 'string' ? cur : '') + '</textarea>';
    }
    pane.innerHTML = html;
    pane.querySelectorAll('.exam-opt').forEach(function (btn) {
      btn.addEventListener('click', function () {
        exam.answers[btn.getAttribute('data-qid')] = btn.getAttribute('data-val');
        renderQuestion();
      });
    });
    pane.querySelectorAll('.match-select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var qid = sel.getAttribute('data-qid');
        var leftIdx = sel.getAttribute('data-left');
        var map2 = exam.answers[qid];
        if (!map2 || typeof map2 !== 'object' || Array.isArray(map2)) map2 = {};
        if (sel.value === '') delete map2[String(leftIdx)];
        else map2[String(leftIdx)] = parseInt(sel.value, 10);
        exam.answers[qid] = map2;
      });
    });
    pane.querySelectorAll('input.exam-input, textarea.exam-input').forEach(function (inp) {
      inp.addEventListener('input', function () {
        exam.answers[inp.getAttribute('data-qid')] = inp.value;
      });
    });
    var dots = $('examDots');
    if (dots) {
      dots.innerHTML = exam.questions.map(function (_, i) {
        return '<span class="dot' + (i === exam.idx ? ' on' : '') + '"></span>';
      }).join('');
    }
  }

  async function submitExam(auto) {
    if (!exam) return;
    stopTimers();
    if (!auto) {
      var msg = lang() === 'ru' ? 'Сдать экзамен?' : (lang() === 'en' ? 'Submit exam?' : 'Шумо мехоҳед супоред?');
      if (!window.confirm(msg)) return;
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
          scoreEl.textContent = (score != null ? score : '—') + (score != null ? '%' : '');
        }
        if (detailEl) {
          detailEl.textContent = (auto ? (t('timeUp') + ' ') : '') + (score != null ? (t('yourScore') + ': ' + score + '%') : t('submitted'));
        }
        if (statusEl) statusEl.textContent = data.passed ? 'Гузашт' : (auto ? t('timeout') : t('submitted'));
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
      if (title) title.textContent = data.title || data.name || 'Олимпиада';
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
        var end = exam.endsAt ? new Date(exam.endsAt).getTime() : (Date.now() + exam.durationSec * 1000);
        paintTimer(Math.max(0, Math.floor((end - Date.now()) / 1000)));
        timerId = setInterval(function () {
          var left = Math.max(0, Math.floor((end - Date.now()) / 1000));
          paintTimer(left);
          if (left <= 0) submitExam(true);
        }, 1000);
      } else {
        var tel = $('examTimer');
        if (tel) tel.textContent = '—';
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
          (o.questionCount || 0) + ' савол · ҳад ' + (o.passScore || 70) + '%</p>' + btn + '</article>';
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
            localStorage.setItem('geo_student_meta', [st.className || '', st.school || ''].filter(Boolean).join(' · '));
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
