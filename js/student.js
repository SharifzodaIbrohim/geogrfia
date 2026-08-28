// Student portal — olympiad UI (aligned with student.html IDs)
(function () {
  'use strict';

  const API = '';
  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function t(key, params) {
    try {
      if (window.GeoI18n && typeof window.GeoI18n.t === 'function') return window.GeoI18n.t(key, params);
      if (typeof window.t === 'function' && window.t !== t) return window.t(key, params);
    } catch (e) {}
    return key;
  }
  function applyStaticI18n() {
    const map = [
      ['examPrevBtn', 'previous'],
      ['examNextBtn', 'next'],
      ['submitExamBtn', 'submitExam'],
      ['logoutBtn', 'logout'],
      ['backToListBtn', 'back'],
    ];
    map.forEach(function (pair) {
      const el = $(pair[0]);
      if (el) el.textContent = t(pair[1]);
    });
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.getAttribute('data-i18n');
      if (!key) return;
      const val = t(key);
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = val;
      else el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
  }

  let student = null;
  let exam = null;
  let timerId = null;
  let autosaveId = null;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>')
      .replace(/"/g, '"');
  }
  function show(el, on) {
    if (!el) return;
    el.classList.toggle('hidden', !on);
  }
  async function api(path, opts) {
    const r = await fetch(API + path, Object.assign({
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
    }, opts || {}));
    let data = null;
    try { data = await r.json(); } catch (e) { data = {}; }
    if (!r.ok) {
      const err = new Error((data && (data.error || data.message)) || ('HTTP ' + r.status));
      err.status = r.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function fmtTime(sec) {
    if (sec == null || sec < 0) return '—';
    sec = Math.floor(sec);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
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

  async function doLogin(id) {
    const data = await api('/api/student/login', {
      method: 'POST',
      body: JSON.stringify({ studentId: id, id: id }),
    });
    student = data.student || data;
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
  }

  function stopTimers() {
    if (timerId) { clearInterval(timerId); timerId = null; }
    if (autosaveId) { clearInterval(autosaveId); autosaveId = null; }
  }

  function startTimers() {
    stopTimers();
    if (!exam) return;
    if (exam.noTimeLimit) {
      const el = $('examTimer');
      if (el) el.textContent = t('noLimit');
    } else {
      timerId = setInterval(function () {
        if (!exam || exam.noTimeLimit) return;
        exam.remainingSec = Math.max(0, (exam.remainingSec || 0) - 1);
        const el = $('examTimer');
        if (el) el.textContent = fmtTime(exam.remainingSec);
        if (exam.remainingSec <= 0) {
          stopTimers();
          submitExam(true);
        }
      }, 1000);
    }
    autosaveId = setInterval(function () { autosave(true); }, 15000);
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
      const id = o.id;
      const title = esc(o.title || o.name || kindLabel);
      const nq = o.questionCount || (o.questions && o.questions.length) || '?';
      const dur = o.durationMin != null ? o.durationMin : o.duration;
      const durTxt = (dur === 0 || dur === '0') ? t('noLimit') : (dur ? (dur + ' ' + t('minutes')) : '');
      const done = o.alreadySubmitted || o.finished;
      const btn = done
        ? '<button class="btn" disabled>' + t('statusParticipated') + '</button>'
        : '<button class="btn primary" data-start="' + esc(id) + '">' + t('startExam') + '</button>';
      return '<div class="card"><h3>' + title + '</h3><p class="muted">' + t('questionsCount') + ': ' + nq +
        (durTxt ? (' · ' + durTxt) : '') + '</p>' + btn + '</div>';
    }).join('');
    box.querySelectorAll('[data-start]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        startExam(btn.getAttribute('data-start'));
      });
    });
  }

  async function loadList() {
    const sid = student && (student.id || student.studentId || student.code);
    const data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(sid));
    const oly = data.olympiads || data.items || [];
    let quizzes = data.quizzes || [];
    if (!quizzes.length) {
      quizzes = oly.filter(function (o) {
        const t = String(o.type || '').toLowerCase();
        return t === 'quiz' || t === 'викторина';
      });
    }
    const pureOly = oly.filter(function (o) {
      const t = String(o.type || '').toLowerCase();
      return t !== 'quiz' && t !== 'викторина';
    });
    renderEventCards($('olympiadList'), pureOly, $('emptyOly'), 'Олимпиада');
    renderEventCards($('quizList'), quizzes, $('emptyQuiz'), 'Викторина');
  }

  async function startExam(olympiadId) {
    const sid = student && (student.id || student.studentId || student.code);
    try {
      const data = await api('/api/olympiads/' + encodeURIComponent(olympiadId) + '/start', {
        method: 'POST',
        body: JSON.stringify({ studentId: sid, id: sid }),
      });
      const durationMin = data.durationMin != null ? Number(data.durationMin) : null;
      const noTimeLimit = durationMin === 0;
      let remaining = data.remainingSec;
      if (!noTimeLimit && remaining == null && durationMin > 0) remaining = durationMin * 60;
      if (!noTimeLimit && remaining == null) remaining = 60 * 60;
      if (noTimeLimit) remaining = null;

      exam = {
        olympiadId: olympiadId,
        attemptId: data.attemptId,
        sessionToken: data.sessionToken,
        questions: data.questions || [],
        remainingSec: remaining,
        noTimeLimit: noTimeLimit,
        durationMin: durationMin,
        answers: {},
        idx: 0,
        title: data.title || 'Олимпиада',
      };
      show($('listView'), false);
      show($('resultView'), false);
      show($('examView'), true);
      if ($('examTitle')) $('examTitle').textContent = exam.title;
      renderExam();
      startTimers();
    } catch (e) {
      alert(e.message || t('errGeneric'));
    }
  }

  function currentQ() {
    if (!exam || !exam.questions) return null;
    return exam.questions[exam.idx] || null;
  }

  function collectCurrentAnswer() {
    if (!exam) return;
    const q = currentQ();
    if (!q) return;
    const qid = String(q.id);
    const qtype = String(q.type || 'single').toLowerCase();
    if (qtype === 'short' || qtype === 'text' || qtype === 'number' || qtype === 'numeric' || qtype === 'open') {
      const inp = $('examTextInput');
      if (inp) {
        const t = inp.value.trim();
        exam.answers[qid] = { t: t, text: t };
      }
    } else if (qtype === 'matching' || qtype === 'match') {
      const selects = document.querySelectorAll('.match-select');
      const m = {};
      selects.forEach(function (sel) {
        const li = sel.getAttribute('data-left');
        if (sel.value !== '') m[String(li)] = parseInt(sel.value, 10);
      });
      exam.answers[qid] = m;
    } else {
      const selected = document.querySelector('.exam-opt.selected');
      if (selected) {
        const i = parseInt(selected.getAttribute('data-i'), 10);
        const t = selected.getAttribute('data-t') || '';
        exam.answers[qid] = { i: i, t: t };
      }
    }
  }

  function renderExam() {
    if (!exam) return;
    const q = currentQ();
    const total = exam.questions.length;
    const n = exam.idx + 1;

    const progress = $('examProgress');
    if (progress) progress.textContent = t('questionXofY', { n: n, total: total });

    const timerEl = $('examTimer');
    if (timerEl) {
      timerEl.textContent = exam.noTimeLimit ? t('noLimit') : fmtTime(exam.remainingSec);
    }

    const dots = $('examDots');
    if (dots) {
      dots.innerHTML = exam.questions.map(function (_, i) {
        const answered = exam.answers[String(exam.questions[i].id)] != null;
        const cls = i === exam.idx ? 'dot active' : (answered ? 'dot done' : 'dot');
        return '<button type="button" class="' + cls + '" data-i="' + i + '">' + (i + 1) + '</button>';
      }).join('');
      dots.querySelectorAll('[data-i]').forEach(function (b) {
        b.addEventListener('click', function () {
          collectCurrentAnswer();
          exam.idx = parseInt(b.getAttribute('data-i'), 10);
          renderExam();
        });
      });
    }

    const pane = $('examQuestionPane');
    if (!pane || !q) {
      if (pane) pane.innerHTML = '<p class="muted">' + t('noQuestion') + '</p>';
      return;
    }

    const selected = exam.answers[String(q.id)];
    let body = '';
    const qtype = String(q.type || 'single').toLowerCase();
    body += '<div class="exam-q">' + esc(q.text || '') + '</div>';

    if (qtype === 'short' || qtype === 'text' || qtype === 'number' || qtype === 'numeric' || qtype === 'open') {
      const val = selected != null ? String(selected.t || selected.text || selected || '') : '';
      body += '<input type="text" class="exam-text-input" id="examTextInput" value="' + esc(val) + '" placeholder="' + t('writeAnswerPlaceholder') + '" autocomplete="off" />';
    } else if (qtype === 'matching' || qtype === 'match') {
      const left = q.leftItems || q.left || [];
      const right = q.rightItems || q.right || [];
      const cur = (selected && typeof selected === 'object' && !Array.isArray(selected)) ? selected : {};
      if (!left.length) {
        body += '<p class="muted">Банди matching холӣ аст</p>';
      } else {
        body += '<div class="exam-match">' + left.map(function (L, li) {
          const sel = cur[String(li)] != null ? String(cur[String(li)]) : '';
          return '<div class="exam-match-row"><span class="match-left">' + esc(L) + '</span>' +
            '<select data-left="' + li + '" class="match-select"><option value="">— ' + t('selectAnswer') + ' —</option>' +
            right.map(function (r, ri) {
              return '<option value="' + ri + '"' + (sel === String(ri) ? ' selected' : '') + '>' +
                esc((LETTERS[ri] || (ri + 1)) + '. ' + r) + '</option>';
            }).join('') +
            '</select></div>';
        }).join('') + '</div>';
      }
    } else {
      const opts = q.options || [];
      body += '<div class="exam-opts" role="listbox">' + opts.map(function (opt, oi) {
        const lab = typeof opt === 'object' ? (opt.text || opt.label || '') : String(opt);
        const isSel = selected && (Number(selected.i) === oi || selected.t === lab);
        return '<button type="button" class="exam-opt' + (isSel ? ' selected' : '') +
          '" data-i="' + oi + '" data-t="' + esc(lab) + '">' +
          '<span class="opt-letter">' + (LETTERS[oi] || (oi + 1)) + '</span><span>' + esc(lab) + '</span></button>';
      }).join('') + '</div>';
    }

    pane.innerHTML = body;
    pane.querySelectorAll('.exam-opt').forEach(function (btn) {
      btn.addEventListener('click', function () {
        pane.querySelectorAll('.exam-opt').forEach(function (b) { b.classList.remove('selected'); });
        btn.classList.add('selected');
        exam.answers[String(q.id)] = {
          i: parseInt(btn.getAttribute('data-i'), 10),
          t: btn.getAttribute('data-t') || '',
        };
      });
    });

    const prev = $('examPrevBtn');
    const next = $('examNextBtn');
    if (prev) prev.disabled = exam.idx <= 0;
    if (next) next.disabled = exam.idx >= total - 1;
  }

  async function autosave(silent) {
    if (!exam) return;
    collectCurrentAnswer();
    const sid = student && (student.id || student.studentId);
    try {
      await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/autosave', {
        method: 'POST',
        body: JSON.stringify({
          studentId: sid,
          id: sid,
          attemptId: exam.attemptId,
          sessionId: exam.attemptId,
          sessionToken: exam.sessionToken,
          answers: exam.answers,
        }),
      });
    } catch (e) {
      if (!silent) console.warn('autosave', e);
    }
  }

  async function submitExam(autoTimeout) {
    if (!exam) return;
    collectCurrentAnswer();
    stopTimers();
    const sid = student && (student.id || student.studentId);
    try {
      const data = await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/exam-submit', {
        method: 'POST',
        body: JSON.stringify({
          studentId: sid,
          id: sid,
          attemptId: exam.attemptId,
          sessionId: exam.attemptId,
          sessionToken: exam.sessionToken,
          answers: exam.answers,
        }),
      });
      exam = null;
      show($('examView'), false);

      const hide = data.hideScore || (data.result && data.result.hideScore);
      show($('resultView'), true);
      if (hide) {
        if ($('resultScore')) $('resultScore').textContent = '✓';
        if ($('resultDetail')) $('resultDetail').textContent =
          data.message || t('waiting');
        if ($('resultStatus')) $('resultStatus').textContent = t('waiting');
      } else {
        const r = Object.assign({}, data, data.result || {});
        const score = r.score != null ? r.score : null;
        const earned = r.earned != null ? r.earned : (r.pointsEarned != null ? r.pointsEarned : null);
        const totalMax = r.totalMax != null ? r.totalMax : (r.maxScore != null ? r.maxScore : null);
        const correct = r.correct != null ? r.correct : null;
        const total = r.total != null ? r.total : null;
        const passThr = r.passScore != null ? r.passScore : (r.pass_score != null ? r.pass_score : 70);
        if ($('resultScore')) {
          if (earned != null && totalMax != null) {
            $('resultScore').textContent = earned + ' / ' + totalMax + ' хол';
          } else {
            $('resultScore').textContent = (score != null ? score : '—') + '%';
          }
        }
        if ($('resultDetail')) {
          const parts = [];
          if (earned != null && totalMax != null) {
            parts.push((score != null ? score : '—') + '%');
          } else if (correct != null && total != null) {
            parts.push(correct + ' ' + t('of') + ' ' + total + ' ' + t('correct'));
          }
          parts.push('Ҳад: ' + passThr + '%');
          $('resultDetail').textContent = parts.join(' · ');
        }
        if ($('resultStatus')) {
          const st = (r.status || '') + '';
          $('resultStatus').textContent = st === 'passed' ? 'Гузашт' : st === 'failed' ? 'Нагузашт' : st;
        }
      }
    } catch (e) {
      alert(e.message || t('errGeneric'));
      if (!autoTimeout) startTimers();
    }
  }

  function bind() {
    const form = $('studentLoginForm');
    if (form) {
      form.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        const id = ($('studentIdInput') && $('studentIdInput').value || '').trim();
        const err = $('loginError');
        try {
          await doLogin(id);
          show($('loginView'), false);
          show($('appView'), true);
          if ($('studentName')) $('studentName').textContent = student.fullName || student.name || id;
          if ($('studentMeta')) {
            $('studentMeta').textContent = [student.className, student.school].filter(Boolean).join(' · ');
          }
          applyStaticI18n();
          loadList();
        } catch (e) {
          if (err) { err.textContent = e.message || t('errLogin'); show(err, true); }
        }
      });
    }
    const logoutBtn = $('logoutBtn');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);

    const prev = $('examPrevBtn');
    const next = $('examNextBtn');
    if (prev) prev.addEventListener('click', function () {
      collectCurrentAnswer();
      if (exam && exam.idx > 0) { exam.idx -= 1; renderExam(); }
    });
    if (next) next.addEventListener('click', function () {
      collectCurrentAnswer();
      if (exam && exam.idx < exam.questions.length - 1) { exam.idx += 1; renderExam(); }
    });
    const submitBtn = $('submitExamBtn');
    if (submitBtn) submitBtn.addEventListener('click', function () {
      if (confirm(t('submitConfirm'))) submitExam(false);
    });
    const back = $('backToListBtn');
    if (back) back.addEventListener('click', function () {
      show($('resultView'), false);
      show($('listView'), true);
      loadList();
    });
  }

  async function boot() {
    bind();
    applyStaticI18n();
    if (window.GeoI18n && typeof window.GeoI18n.onLang === 'function') {
      window.GeoI18n.onLang(function () {
        applyStaticI18n();
        if (exam) renderExam();
        else if (student) loadList();
      });
    }
    const saved = loadLocalStudent();
    if (saved && (saved.id || saved.studentId)) {
      try {
        student = saved;
        show($('loginView'), false);
        show($('appView'), true);
        if ($('studentName')) $('studentName').textContent = student.fullName || student.name || student.id;
        if ($('studentMeta')) $('studentMeta').textContent = [student.className, student.school].filter(Boolean).join(' · ');
        await loadList();
      } catch (e) {
        logout();
      }
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
