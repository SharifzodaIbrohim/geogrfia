/**
 * Admin Results Review — dark modal, per-question A/B/C/D, print.
 * Plain full file (no loader / PLACEHOLDER).
 */
(function () {
  'use strict';

  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function injectStyles() {
    if (document.getElementById('admin-results-review-css')) return;
    const s = document.createElement('style');
    s.id = 'admin-results-review-css';
    s.textContent = [
      '.rev-modal{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:12px}',
      '.rev-modal.hidden{display:none!important}',
      '.rev-box{background:#0f172a;color:#e2e8f0;max-width:920px;width:100%;max-height:92vh;overflow:auto;border-radius:14px;padding:18px 20px;box-shadow:0 16px 48px rgba(0,0,0,.55);border:1px solid #1e293b}',
      '.rev-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:12px}',
      '.rev-head h2{margin:0;font-size:1.2rem;color:#f8fafc}',
      '.rev-meta{font-size:.9rem;color:#94a3b8;margin:6px 0 10px;line-height:1.45}',
      '.rev-stats{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 14px}',
      '.rev-stats span{background:#1e293b;padding:5px 12px;border-radius:999px;font-size:.85rem;color:#cbd5e1;border:1px solid #334155}',
      '.rev-item{border:1px solid #334155;border-radius:10px;padding:12px 14px;margin-bottom:10px;background:#111827}',
      '.rev-item.ok{border-color:#166534;background:#052e16}',
      '.rev-item.bad{border-color:#991b1b;background:#450a0a}',
      '.rev-item.blank{border-color:#475569;background:#1e293b}',
      '.rev-q{font-weight:600;margin-bottom:8px;color:#f1f5f9}',
      '.rev-opts{margin:6px 0 8px;padding-left:0;list-style:none}',
      '.rev-opts li{padding:3px 0;color:#94a3b8;font-size:.9rem}',
      '.rev-opts li.pick{color:#38bdf8;font-weight:600}',
      '.rev-opts li.correct-opt{color:#4ade80}',
      '.rev-ans{font-size:.92rem;margin:4px 0;color:#cbd5e1}',
      '.rev-tag{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:6px;margin-left:6px;vertical-align:middle}',
      '.rev-tag-ok{background:#14532d;color:#bbf7d0}',
      '.rev-tag-bad{background:#7f1d1d;color:#fecaca}',
      '.rev-tag-blank{background:#334155;color:#94a3b8}',
      '.rev-actions{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}',
      '.rev-actions button{cursor:pointer;padding:9px 16px;border-radius:8px;border:1px solid #475569;background:#1e293b;color:#e2e8f0;font-size:.95rem}',
      '.rev-actions .primary{background:#0d9488;color:#fff;border-color:#0d9488}',
      '.rev-close{background:transparent;border:none;color:#94a3b8;font-size:1.25rem;cursor:pointer;padding:4px 8px}',
      '.rev-empty{padding:24px 12px;text-align:center;color:#94a3b8}',
      '@media print{.rev-modal{position:static;background:#fff;padding:0}.rev-box{background:#fff;color:#111;box-shadow:none;max-height:none;border:none}.rev-item{background:#fff;color:#111;border-color:#ccc}.rev-item.ok{background:#f0fdf4}.rev-item.bad{background:#fef2f2}.rev-q,.rev-ans{color:#111}.rev-actions,.rev-close{display:none!important}}',
    ].join('');
    document.head.appendChild(s);
  }

  function ensureModal() {
    if (document.getElementById('attemptReviewModal')) return;
    const d = document.createElement('div');
    d.id = 'attemptReviewModal';
    d.className = 'rev-modal hidden';
    d.innerHTML =
      '<div class="rev-box" role="dialog" aria-modal="true">' +
      '<div class="rev-head"><div><h2 id="revTitle">Баррасӣ</h2><div class="rev-meta" id="revMeta"></div></div>' +
      '<button type="button" class="rev-close" id="revCloseBtn" aria-label="Close">✕</button></div>' +
      '<div class="rev-stats" id="revStats"></div>' +
      '<div id="revBody"></div>' +
      '<div class="rev-actions">' +
      '<button type="button" class="primary" id="revPrintBtn">Чоп кардан</button>' +
      '<button type="button" id="revCloseBtn2">Пӯшидан</button>' +
      '</div></div>';
    document.body.appendChild(d);
    d.addEventListener('click', function (e) { if (e.target === d) closeReview(); });
    document.getElementById('revCloseBtn').onclick = closeReview;
    document.getElementById('revCloseBtn2').onclick = closeReview;
    document.getElementById('revPrintBtn').onclick = function () { window.print(); };
  }

  function closeReview() {
    const m = document.getElementById('attemptReviewModal');
    if (m) m.classList.add('hidden');
  }

  function esc(s) {
    if (typeof window.esc === 'function') return window.esc(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>')
      .replace(/"/g, '"');
  }

  function api(path, opts) {
    if (typeof window.api === 'function') return window.api(path, opts);
    const headers = Object.assign({ 'Content-Type': 'application/json' }, (opts && opts.headers) || {});
    try {
      const t = localStorage.getItem('adminToken') || sessionStorage.getItem('adminToken');
      if (t) headers['X-Admin-Token'] = t;
    } catch (e) {}
    return fetch(path, Object.assign({}, opts, { headers: headers, credentials: 'include' })).then(async function (r) {
      const data = await r.json().catch(function () { return {}; });
      if (!r.ok) throw Object.assign(new Error(data.error || r.statusText), { status: r.status, data: data });
      return data;
    });
  }

  function renderOptions(it) {
    const opts = it.options || it.choices || [];
    if (!opts.length) return '';
    const student = String(it.studentAnswer != null ? it.studentAnswer : (it.selectedText || '')).trim().toLowerCase();
    const correct = String(it.correctAnswer != null ? it.correctAnswer : (it.correctText || '')).trim().toLowerCase();
    let html = '<ul class="rev-opts">';
    opts.forEach(function (o, i) {
      const text = typeof o === 'string' ? o : (o.text || o.label || o.value || '');
      const letter = LETTERS[i] || String(i + 1);
      const low = String(text).trim().toLowerCase();
      const cls = [];
      if (student && low === student) cls.push('pick');
      if (correct && low === correct) cls.push('correct-opt');
      html += '<li class="' + cls.join(' ') + '">' + letter + ') ' + esc(text) + '</li>';
    });
    html += '</ul>';
    return html;
  }

  async function showReview(attemptId, fallbackName, olympiadTitle) {
    injectStyles();
    ensureModal();
    const modal = document.getElementById('attemptReviewModal');
    const body = document.getElementById('revBody');
    const meta = document.getElementById('revMeta');
    const stats = document.getElementById('revStats');
    const title = document.getElementById('revTitle');
    title.textContent = 'Баррасӣ';
    meta.textContent = 'Боргирӣ…';
    body.innerHTML = '';
    stats.innerHTML = '';
    modal.classList.remove('hidden');
    try {
      const data = await api('/api/admin/attempts/' + encodeURIComponent(attemptId) + '/review');
      const status = String(data.status || '').toLowerCase();
      const name = data.studentName || data.fullName || fallbackName || '—';
      const oly = data.olympiadTitle || olympiadTitle || '';
      const school = data.school || data.studentSchool || '';
      const klass = data.className || data.studentClass || '';
      const code = data.studentCode || data.studentId || '';
      title.textContent = name;
      meta.innerHTML = [
        oly ? ('Олимпиада: ' + esc(oly)) : '',
        school ? ('Мактаб: ' + esc(school)) : '',
        klass ? ('Синф: ' + esc(klass)) : '',
        code ? ('ID: ' + esc(code)) : '',
        data.score != null ? ('Хол: ' + esc(data.score) + (data.totalMax != null ? '' : '%')) : '',
        (data.earned != null && data.totalMax != null) ? (esc(data.earned) + ' / ' + esc(data.totalMax)) : '',
        status ? ('Статус: ' + esc(data.status)) : '',
      ].filter(Boolean).join(' · ');

      if (status === 'in_progress' || status === 'started' || status === 'active') {
        body.innerHTML = '<div class="rev-empty">Ҳанӯз супорида нашудааст. Сессия дар ҳоли иҷро аст.</div>';
        stats.innerHTML = '';
        return;
      }

      const st = data.stats || {};
      stats.innerHTML =
        '<span>Дуруст: ' + (st.correct != null ? st.correct : data.correctCount || 0) + '</span>' +
        '<span>Нодуруст: ' + (st.wrong != null ? st.wrong : data.wrongCount || 0) + '</span>' +
        '<span>Беҷавоб: ' + (st.blank != null ? st.blank : data.blankCount || 0) + '</span>' +
        (data.earned != null || data.correct != null
          ? '<span>Ҳол: ' + (data.earned != null ? data.earned : data.correct) +
            (data.totalMax != null || data.total != null ? (' / ' + (data.totalMax != null ? data.totalMax : data.total)) : '') +
            '</span>'
          : '');

      const items = data.items || [];
      if (!items.length) {
        body.innerHTML = '<div class="rev-empty">Ҷавобҳо сабт нашудаанд ё холӣ. Агар submit нав бошад — саҳифаро навсозӣ кунед; агар кӯҳна бошад, ҷавобҳо дар DB нестанд.</div>';
      } else {
        body.innerHTML = items.map(function (it, idx) {
          var cls = it.isBlank ? 'blank' : (it.isCorrect ? 'ok' : 'bad');
          var tag = it.resultLabel || (it.isBlank ? 'Беҷавоб' : (it.isCorrect ? 'Дуруст' : 'Нодуруст'));
          var tagCls = it.isBlank ? 'rev-tag-blank' : (it.isCorrect ? 'rev-tag-ok' : 'rev-tag-bad');
          return '<div class="rev-item ' + cls + '">' +
            '<div class="rev-q">' + (it.index || (idx + 1)) + '. ' + esc(it.question || it.text || '') +
            ' <span class="rev-tag ' + tagCls + '">' + esc(tag) + '</span></div>' +
            renderOptions(it) +
            '<div class="rev-ans">Ҷавоби хонанда: <b>' + esc(it.studentAnswer != null ? it.studentAnswer : (it.selectedText || '—')) + '</b></div>' +
            '<div class="rev-ans">Ҷавоби дуруст: <b>' + esc(it.correctAnswer != null ? it.correctAnswer : (it.correctText || '—')) + '</b></div>' +
            (it.points != null || it.maxScore != null
              ? '<div class="rev-ans">Хол: ' + esc(it.points != null ? it.points : 0) +
                (it.maxScore != null ? (' / ' + it.maxScore) : '') + '</div>'
              : '') +
            '</div>';
        }).join('');
      }
    } catch (err) {
      body.innerHTML = '<div class="rev-empty">Хато: ' + esc(err.message || String(err)) + '</div>';
      meta.textContent = '';
    }
  }

  window.__openAttemptReview = showReview;
  window.openAttemptReview = showReview;

  function bindResultsClicks() {
    document.addEventListener('click', function (e) {
      const row = e.target.closest && e.target.closest('[data-attempt-id], tr[data-id], .result-row, .results-row');
      if (!row) return;
      const aid = row.getAttribute('data-attempt-id') || row.getAttribute('data-id') || row.dataset.attemptId;
      if (!aid) return;
      if (e.target.closest('button, a, input')) return;
      e.preventDefault();
      const name = row.getAttribute('data-name') || '';
      const title = row.getAttribute('data-olympiad') || '';
      showReview(aid, name, title);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindResultsClicks);
  } else {
    bindResultsClicks();
  }

  console.log('[admin-results-review] dark modal ready');
})();
