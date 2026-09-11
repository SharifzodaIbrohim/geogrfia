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
      timeUp: 'Вақт тамом шуд.', yourScore: 'Холи шумо', pendingReview: 'Дар баррасӣ',
      timeout: 'Вақт тамом', questionLabel: 'Савол', selectPair: '— интихоб —'
    },
    ru: {
      previous: '← Назад', next: 'Далее →', submitExam: 'Сдать', logout: 'Выйти',
      back: 'Назад', startExam: 'Начать', submitted: 'Сдано',
      timeUp: 'Время вышло.', yourScore: 'Ваш балл', pendingReview: 'На проверке',
      timeout: 'Время вышло', questionLabel: 'Вопрос', selectPair: '— выбрать —'
    },
    en: {
      previous: '← Previous', next: 'Next →', submitExam: 'Submit', logout: 'Logout',
      back: 'Back', startExam: 'Start', submitted: 'Submitted',
      timeUp: 'Time is up.', yourScore: 'Your score', pendingReview: 'Pending review',
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
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>')
      .replace(/"/g, '"');
  }

  function show(el, on) {
    if (!el) return;
    el.classList.toggle('hidden', !on);
    el.style.display = on ? '' : 'none';
  }

  function studentId() {
    return localStorage.getItem('geo_student_id') || sessionStorage.getItem('geo_student_id') || '';
  }

  function authHeaders() {
    var h = { 'Content-Type': 'application/json' };
    var sid = studentId();
    if (sid) h['X-Student-Id'] = sid;
    var tok = localStorage.getItem('geo_student_token') || '';
    if (tok) h['Authorization'] = 'Bearer ' + tok;
    return h;
  }

  async function api(path, options) {
    options = options || {};
    var res = await fetch(path, Object.assign({}, options, {
      headers: Object.assign(authHeaders(), options.headers || {}),
      credentials: 'include'
    }));
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.message || ('Хато ' + res.status));
    return data;
  }

  function stopTimers() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  function normalizeQ(q, i) {
    if (!q) return { id: String(i), text: '', type: 'single', options: [], leftItems: [], rightItems: [] };
    var opts = q.options || q.choices || [];
    opts = opts.map(function (o, j) {
      if (typeof o === 'string') return { text: o, letter: LETTERS[j] || String(j) };
      return {
        text: o.text || o.label || o.value || String(o),
        letter: o.letter || LETTERS[j] || String(j),
        id: o.id != null ? o.id : j
      };
    });
    var left = q.leftItems || q.left || [];
    var right = q.rightItems || q.right || [];
    if (!Array.isArray(left)) left = [];
    if (!Array.isArray(right)) right = [];
    return {
      id: q.id != null ? String(q.id) : String(i),
      text: q.text || q.question || q.title || '',
      type: (q.type || q.qtype || 'single').toLowerCase(),
      options: opts,
      leftItems: left.map(function (x) { return String(x); }),
      rightItems: right.map(function (x) { return String(x); })
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
    if (q.type === 'single' || q.type === 'choice' || q.type === 'mcq' || (!q.type && !(q.leftItems && q.leftItems.length))) {
      html += '<div class="exam-opts">';
      q.options.forEach(function (opt, j) {
        var val = opt.id != null ? opt.id : j;
        var sel = String(cur) === String(val) || String(cur) === String(j) || cur === opt.text;
        html += '<button type="button" class="exam-opt' + (sel ? ' selected' : '') + '" data-qid="' + esc(q.id) + '" data-val="' + esc(val) + '">' +
          '<span class="opt-letter">' + esc(opt.letter || LETTERS[j]) + '</span> ' + esc(opt.text) + '</button>';
      });
      html += '</div>';
    } else if (q.type === 'matching' || q.type === 'match') {
      var map = (cur && typeof cur === 'object' && !Array.isArray(cur)) ? cur : {};
      var left = q.leftItems || [];
      var right = q.rightItems || [];
      html += '<div class="exam-match">';
      left.forEach(function (L, li) {
        var selVal = map[String(li)];
        if (selVal === undefined || selVal === null) selVal = '';
        html += '<div class="exam-match-row">' +
          '<span class="match-left" style="min-width:40%;flex:1">' + esc(L) + '</span>' +
          '<select class="exam-input match-select" data-qid="' + esc(q.id) + '" data-left="' + li + '" style="flex:1;min-width:120px">' +
          '<option value="">' + esc(t('selectPair')) + '</option>';
        right.forEach(function (R, ri) {
          var selected = String(selVal) === String(ri);
          html += '<option value="' + ri + '"' + (selected ? ' selected' : '') + '>' + esc(R) + '</option>';
        });
        html += '</select></div>';
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
        if (sel.value === '') {
          delete map2[String(leftIdx)];
        } else {
          map2[String(leftIdx)] = parseInt(sel.value, 10);
        }
        exam.answers[qid] = map2;
      });
    });
    pane.querySelectorAll('.exam-input:not(.match-select)').forEach(function (inp) {
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
    if (!auto) {
      if (!window.confirm(lang() === 'ru' ? 'Сдать экзамен?' : lang() === 'en' ? 'Submit exam?' : 'Шумо мехоҳед супоред?')) {
        return;
      }
    }
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/exam-submit', {
        method: 'POST',
        body: JSON.stringify({
          studentId: studentId(),
          attemptId: exam.attemptId,
          answers: exam.answers
        })
      });
      var score = data.score != null ? data.score : data.percent;
      var hide = !!(data.hideScore || data.showResultsToStudents === false);
      var scoreEl = $('resultScore');
      var detailEl = $('resultDetail');
      var statusEl = $('resultStatus');
      if (hide) {
        if (scoreEl) scoreEl.style.display = 'none';
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
      }
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  async function startExam(olympiadId) {
    stopTimers();
    try {
      var data = await api('/api/olympiads/' + encodeURIComponent(olympiadId) + '/exam-start', {
        method: 'POST',
        body: JSON.stringify({ studentId: studentId() })
      });
      var qs = data.questions || (data.exam && data.exam.questions) || [];
      exam = {
        olympiadId: olympiadId,
        attemptId: data.attemptId || data.id,
        questions: qs,
        answers: data.answers || {},
        idx: 0,
        endsAt: data.endsAt || data.endAt || null,
        durationSec: data.durationSec || 0
      };
      show($('listView'), false);
      show($('resultView'), false);
      show($('examView'), true);
      renderQuestion();
      if (exam.endsAt || exam.durationSec) {
        var end = exam.endsAt ? new Date(exam.endsAt).getTime() : (Date.now() + exam.durationSec * 1000);
        timerId = setInterval(function () {
          var left = Math.max(0, Math.floor((end - Date.now()) / 1000));
          var el = $('examTimer');
          if (el) {
            var m = Math.floor(left / 60);
            var s = left % 60;
            el.textContent = m + ':' + (s < 10 ? '0' : '') + s;
          }
          if (left <= 0) submitExam(true);
        }, 1000);
      }
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  async function loadList() {
    try {
      var data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(studentId()));
      var list = data.olympiads || data.items || [];
      var box = $('olympiadList');
      if (!box) return;
      if (!list.length) {
        box.innerHTML = '<p class="muted">Олимпиада нест</p>';
        return;
      }
      box.innerHTML = list.map(function (o) {
        var nq = o.questionCount || (o.questions && o.questions.length) || '?';
        var done = !!(o.alreadySubmitted || o.finished || o.submitted);
        var btn;
        if (done) {
          btn = '<button class="btn" disabled>' + esc(t('submitted')) + '</button>';
        } else {
          btn = '<button class="btn primary start-exam" data-id="' + esc(o.id) + '">' + esc(t('startExam')) + '</button>';
        }
        return '<div class="card oly-card" style="margin-bottom:.75rem;padding:1rem">' +
          '<strong>' + esc(o.title || 'Олимпиада') + '</strong>' +
          '<div class="muted">Саволҳо: ' + nq + '</div>' + btn + '</div>';
      }).join('');
      box.querySelectorAll('.start-exam').forEach(function (b) {
        b.addEventListener('click', function () {
          startExam(b.getAttribute('data-id'));
        });
      });
    } catch (e) {
      console.error(e);
    }
  }

  function bindNav() {
    var prev = $('prevQuestionBtn');
    var next = $('nextQuestionBtn');
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
    if (sub) sub.addEventListener('click', function () {
      submitExam(false);
    });
  }

  function init() {
    bindNav();
    if (studentId()) {
      show($('loginView'), false);
      show($('appView') || $('listView'), true);
      loadList();
    }
    var form = $('studentLoginForm');
    if (form) {
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        var id = ($('studentIdInput') || {}).value || '';
        id = String(id).trim();
        if (!id) return;
        try {
          var data = await api('/api/student/login', {
            method: 'POST',
            body: JSON.stringify({ studentId: id })
          });
          localStorage.setItem('geo_student_id', data.studentId || id);
          if (data.token) localStorage.setItem('geo_student_token', data.token);
          show($('loginView'), false);
          show($('appView') || $('listView'), true);
          loadList();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    }
    var lo = $('logoutBtn');
    if (lo) lo.addEventListener('click', function () {
      localStorage.removeItem('geo_student_id');
      localStorage.removeItem('geo_student_token');
      location.reload();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
