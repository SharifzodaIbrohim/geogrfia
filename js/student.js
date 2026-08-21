// Student portal — olympiad UI (aligned with student.html IDs)
(function () {
  'use strict';

  const API = '';
  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

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
      if (el) el.textContent = 'Бе маҳдуд';
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

  async function loadList() {
    const sid = student && (student.id || student.studentId || student.code);
    const data = await api('/api/student/olympiads?studentId=' + encodeURIComponent(sid));
    const list = data.olympiads || data.items || [];
    const box = $('olympiadList');
    if (!box) return;
    if (!list.length) {
      box.innerHTML = '';
      show($('emptyOly'), true);
      return;
    }
    show($('emptyOly'), false);
    box.innerHTML = list.map(function (o) {
      const id = o.id;
      const title = esc(o.title || o.name || 'Олимпиада');
      const nq = o.questionCount || (o.questions && o.questions.length) || '?';
      const dur = o.durationMin != null ? o.durationMin : o.duration;
      const durTxt = (dur === 0 || dur === '0') ? 'Бе вақт' : (dur ? (dur + ' дақ') : '');
      const done = o.alreadySubmitted || o.finished;
      const btn = done
        ? '<button class="btn" disabled>Супорида шуд</button>'
        : '<button class="btn primary" data-start="' + esc(id) + '">Оғоз</button>';
      return '<div class="card"><h3>' + title + '</h3><p class="muted">Саволҳо: ' + nq +
        (durTxt ? (' · ' + durTxt) : '') + '</p>' + btn + '</div>';
    }).join('');
    box.querySelectorAll('[data-start]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        startExam(btn.getAttribute('data-start'));
      });
    });
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
      alert(e.message || 'Оғоз нашуд');
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
    if (progress) progress.textContent = 'Савол ' + n + ' / ' + total;

    const timerEl = $('examTimer');
    if (timerEl) {
      timerEl.textContent = exam.noTimeLimit ? 'Бе маҳдуд' : fmtTime(exam.remainingSec);
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
      if (pane) pane.innerHTML = '<p class="muted">Савол нест</p>';
      return;
    }

    const selected = exam.answers[String(q.id)];
    let body = '';
    const qtype = String(q.type || 'single').toLowerCase();
    body += '<div class="exam-q">' + esc(q.text || '') + '</div>';

    if (qtype === 'short' || qtype === 'text' || qtype === 'number' || qtype === 'numeric' || qtype === 'open') {
      const val = selected != null ? String(selected.t || selected.text || selected || '') : '';
      body += '<input type="text" class="exam-text-input" id="examTextInput" value="' + esc(val) + '" placeholder="Ҷавобро нависед..." autocomplete="off" />';
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
            '<select data-left="' + li + '" class="match-select"><option value="">— интихоб —</option>' +
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
          data.message || 'Шумо бо муваффақият супоридед. Натиҷа баъдтар эълон мешавад.';
        if ($('resultStatus')) $('resultStatus').textContent = 'Интизор';
      } else {
        const score = data.score != null ? data.score : (data.result && data.result.score);
        const correct = data.correct != null ? data.correct : (data.result && data.result.correct);
        const total = data.total != null ? data.total : (data.result && data.result.total);
        if ($('resultScore')) $('resultScore').textContent = (score != null ? score : '—') + '%';
        if ($('resultDetail')) {
          $('resultDetail').textContent =
            (correct != null && total != null) ? (correct + ' аз ' + total + ' дуруст') : '';
        }
        if ($('resultStatus')) {
          $('resultStatus').textContent = (data.status || (data.result && data.result.status) || '') + '';
        }
      }
    } catch (e) {
      alert(e.message || 'Супориш нашуд');
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
          loadList();
        } catch (e) {
          if (err) { err.textContent = e.message || 'Хато'; show(err, true); }
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
      if (confirm('Супоридан?')) submitExam(false);
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
