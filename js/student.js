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
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
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
    let data = null;
    try {
      data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(sid || ''));
    } catch (e) {
      // Fallback if /api/student/olympiads missing (404) — use public active list
      try {
        const act = await api('/api/olympiads/active');
        data = { olympiads: act.olympiads || act.items || [], quizzes: act.quizzes || [] };
      } catch (e2) {
        data = { olympiads: [], quizzes: [] };
      }
    }
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
        idx: 0,
        answers: {},
      };
      show($('listView'), false);
      show($('examView'), true);
      renderQuestion();
      startTimers();
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  function renderQuestion() {
    if (!exam || !exam.questions.length) return;
    const q = exam.questions[exam.idx];
    if (!q) return;
    const box = $('examQuestion');
    if (!box) return;
    const qtype = String(q.type || 'single').toLowerCase();
    let html = '<div class="q-text">' + esc(q.text || q.question || '') + '</div>';
    if (qtype === 'single' || qtype === 'multiple' || !qtype) {
      const opts = q.options || [];
      html += '<div class="exam-opts">' + opts.map(function (opt, i) {
        const letter = LETTERS[i] || String(i + 1);
        const val = typeof opt === 'string' ? opt : (opt.text || opt.label || '');
        const checked = exam.answers[q.id] === i || exam.answers[q.id] === String(i);
        return '<label class="exam-opt' + (checked ? ' selected' : '') + '"><input type="radio" name="ans" value="' + i + '"' +
          (checked ? ' checked' : '') + ' /> <span>' + letter + '. ' + esc(val) + '</span></label>';
      }).join('') + '</div>';
    } else if (qtype === 'short' || qtype === 'text') {
      const cur = exam.answers[q.id] != null ? exam.answers[q.id] : '';
      html += '<textarea class="exam-text" rows="3">' + esc(cur) + '</textarea>';
    } else if (qtype === 'matching') {
      const pairs = q.pairs || q.left || [];
      html += '<div class="exam-match">' + (pairs.map(function (p, i) {
        return '<div>' + esc(p.left || p) + '</div>';
      }).join('')) + '</div>';
    }
    box.innerHTML = html;
    box.querySelectorAll('input[name=ans]').forEach(function (inp) {
      inp.addEventListener('change', function () {
        exam.answers[q.id] = Number(inp.value);
        box.querySelectorAll('.exam-opt').forEach(function (lab) { lab.classList.remove('selected'); });
        if (inp.closest) inp.closest('.exam-opt').classList.add('selected');
      });
    });
    const ta = box.querySelector('textarea.exam-text');
    if (ta) {
      ta.addEventListener('input', function () {
        exam.answers[q.id] = ta.value;
      });
    }
    const dots = $('examDots');
    if (dots) {
      dots.innerHTML = exam.questions.map(function (qq, i) {
        const answered = exam.answers[qq.id] != null && exam.answers[qq.id] !== '';
        const cls = i === exam.idx ? 'dot active' : (answered ? 'dot done' : 'dot');
        return '<span class="' + cls + '" data-i="' + i + '"></span>';
      }).join('');
      dots.querySelectorAll('[data-i]').forEach(function (d) {
        d.addEventListener('click', function () {
          exam.idx = Number(d.getAttribute('data-i'));
          renderQuestion();
        });
      });
    }
    const prog = $('examProgress');
    if (prog) prog.textContent = (exam.idx + 1) + ' / ' + exam.questions.length;
  }

  async function autosave(silent) {
    if (!exam) return;
    const sid = student && (student.id || student.studentId || student.code);
    try {
      await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/autosave', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: exam.attemptId,
          sessionToken: exam.sessionToken,
          studentId: sid,
          answers: exam.answers,
        }),
      });
    } catch (e) {
      if (!silent) console.warn('autosave', e);
    }
  }

  async function submitExam(auto) {
    if (!exam) return;
    stopTimers();
    const sid = student && (student.id || student.studentId || student.code);
    try {
      const data = await api('/api/olympiads/' + encodeURIComponent(exam.olympiadId) + '/exam-submit', {
        method: 'POST',
        body: JSON.stringify({
          attemptId: exam.attemptId,
          sessionToken: exam.sessionToken,
          studentId: sid,
          answers: exam.answers,
          timedOut: !!auto,
        }),
      });
      const score = data.score != null ? data.score : data.percent;
      const msg = (auto ? (t('timeUp') + ' ') : '') +
        (score != null ? (t('yourScore') + ': ' + score + '%') : t('submitted'));
      alert(msg);
      exam = null;
      show($('examView'), false);
      show($('listView'), true);
      loadList();
    } catch (e) {
      alert(e.message || String(e));
      startTimers();
    }
  }

  function bindUI() {
    const loginForm = $('studentLoginForm');
    if (loginForm) {
      loginForm.addEventListener('submit', async function (ev) {
        ev.preventDefault();
        const inp = $('studentIdInput') || $('studentLogin');
        const id = (inp && inp.value || '').trim();
        if (!id) return;
        try {
          await doLogin(id);
          show($('loginView'), false);
          show($('appView'), true);
          const nameEl = $('studentName');
          if (nameEl && student) {
            nameEl.textContent = (student.fullName || student.name || '') +
              (student.className ? (' · ' + student.className) : '') +
              (student.school ? (' · ' + student.school) : '');
          }
          loadList();
        } catch (e) {
          const err = $('loginError');
          if (err) { err.textContent = e.message || String(e); show(err, true); }
          else alert(e.message || String(e));
        }
      });
    }
    const lo = $('logoutBtn');
    if (lo) lo.addEventListener('click', logout);
    const prev = $('examPrevBtn');
    if (prev) prev.addEventListener('click', function () {
      if (!exam) return;
      exam.idx = Math.max(0, exam.idx - 1);
      renderQuestion();
    });
    const next = $('examNextBtn');
    if (next) next.addEventListener('click', function () {
      if (!exam) return;
      exam.idx = Math.min(exam.questions.length - 1, exam.idx + 1);
      renderQuestion();
    });
    const sub = $('submitExamBtn');
    if (sub) sub.addEventListener('click', function () { submitExam(false); });
    const back = $('backToListBtn');
    if (back) back.addEventListener('click', function () {
      if (exam && !confirm(t('leaveExam'))) return;
      stopTimers();
      exam = null;
      show($('examView'), false);
      show($('listView'), true);
      loadList();
    });
  }

  function init() {
    bindUI();
    applyStaticI18n();
    const saved = loadLocalStudent();
    if (saved && (saved.id || saved.studentId || saved.code)) {
      student = saved;
      show($('loginView'), false);
      show($('appView'), true);
      const nameEl = $('studentName');
      if (nameEl) {
        nameEl.textContent = (student.fullName || student.name || '') +
          (student.className ? (' · ' + student.className) : '') +
          (student.school ? (' · ' + student.school) : '');
      }
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
