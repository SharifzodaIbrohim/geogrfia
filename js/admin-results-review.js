/**
 * Admin Results Review — click student row → full answer detail + print.
 * Depends on admin.js (api, esc, displayName, statusLabel, token).
 */
(function () {
  'use strict';

  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function injectStyles() {
    if (document.getElementById('admin-results-review-css')) return;
    const s = document.createElement('style');
    s.id = 'admin-results-review-css';
    s.textContent = [
      '.rev-modal{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:12px}',
      '.rev-modal.hidden{display:none!important}',
      '.rev-box{background:#fff;color:#111;max-width:920px;width:100%;max-height:92vh;overflow:auto;border-radius:12px;padding:16px 18px;box-shadow:0 12px 40px rgba(0,0,0,.25)}',
      '.rev-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:12px}',
      '.rev-head h2{margin:0;font-size:1.15rem}',
      '.rev-meta{font-size:.9rem;color:#444;margin:4px 0 10px}',
      '.rev-stats{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 14px}',
      '.rev-stats span{background:#f1f5f9;padding:4px 10px;border-radius:999px;font-size:.85rem}',
      '.rev-item{border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin-bottom:10px}',
      '.rev-item.ok{border-color:#86efac;background:#f0fdf4}',
      '.rev-item.bad{border-color:#fca5a5;background:#fef2f2}',
      '.rev-item.blank{border-color:#e2e8f0;background:#f8fafc}',
      '.rev-q{font-weight:600;margin-bottom:6px}',
      '.rev-ans{font-size:.92rem;margin:3px 0}',
      '.rev-tag{display:inline-block;font-size:.75rem;padding:2px 8px;border-radius:6px;margin-left:6px}',
      '.rev-tag-ok{background:#bbf7d0;color:#166534}',
      '.rev-tag-bad{background:#fecaca;color:#991b1b}',
      '.rev-tag-blank{background:#e2e8f0;color:#475569}',
      '.rev-actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}',
      '.rev-actions button{cursor:pointer;padding:8px 14px;border-radius:8px;border:1px solid #cbd5e1;background:#fff}',
      '.rev-actions .primary{background:#0f766e;color:#fff;border-color:#0f766e}',
      '@media print{.rev-modal{position:static;background:#fff;padding:0}.rev-box{box-shadow:none;max-height:none}.rev-actions,.rev-close{display:none!important}}',
    ].join('');
    document.head.appendChild(s);
  }

  function ensureModal() {
    if (document.getElementById('attemptReviewModal')) return;
    const d = document.createElement('div');
    d.id = 'attemptReviewModal';
    d.className = 'rev-modal hidden';
    d.innerHTML = '<div class="rev-box" role="dialog" aria-modal="true"><div class="rev-head"><div><h2 id="revTitle">Баррасӣ</h2><div class="rev-meta" id="revMeta"></div></div><button type="button" class="rev-close" id="revCloseBtn" aria-label="Close">✕</button></div><div class="rev-stats" id="revStats"></div><div id="revBody"></div><div class="rev-actions"><button type="button" class="primary" id="revPrintBtn">Чоп</button><button type="button" id="revCloseBtn2">Пӯшидан</button></div></div>';
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
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function api(path, opts) {
    if (typeof window.api === 'function') return window.api(path, opts);
    const headers = Object.assign({ 'Content-Type': 'application/json' }, (opts && opts.headers) || {});
    try {
      const t = localStorage.getItem('adminToken') || sessionStorage.getItem('adminToken');
      if (t) headers['X-Admin-Token'] = t;
    } catch (e) {}
    return fetch(path, Object.assign({}, opts, { headers, credentials: 'include' })).then(async function (r) {
      const data = await r.json().catch(function () { return {}; });
      if (!r.ok) throw Object.assign(new Error(data.error || r.statusText), { status: r.status, data: data });
      return data;
    });
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
      const name = data.studentName || data.fullName || fallbackName || 'Иштирокчӣ';
      const oly = data.olympiadTitle || olympiadTitle || '';
      title.textContent = name;
      meta.textContent = [oly, data.status, data.score != null ? ('Хол: ' + data.score + '%') : ''].filter(Boolean).join(' · ');
      const st = data.stats || {};
      stats.innerHTML =
        '<span>Дуруст: ' + (st.correct != null ? st.correct : data.correctCount || 0) + '</span>' +
        '<span>Нодуруст: ' + (st.wrong != null ? st.wrong : data.wrongCount || 0) + '</span>' +
        '<span>Беҷавоб: ' + (st.blank != null ? st.blank : data.blankCount || 0) + '</span>' +
        (data.earned != null ? '<span>Ҳол: ' + data.earned + (data.totalMax != null ? (' / ' + data.totalMax) : '') + '</span>' : '');
      const items = data.items || [];
      if (!items.length) {
        body.innerHTML = '<p>Ҷавобҳо сабт нашудаанд ё холӣ.</p>';
      } else {
        body.innerHTML = items.map(function (it, idx) {
          var cls = it.isBlank ? 'blank' : (it.isCorrect ? 'ok' : 'bad');
          var tag = it.resultLabel || (it.isBlank ? 'Беҷавоб' : (it.isCorrect ? 'Дуруст' : 'Нодуруст'));
          var tagCls = it.isBlank ? 'rev-tag-blank' : (it.isCorrect ? 'rev-tag-ok' : 'rev-tag-bad');
          return '<div class="rev-item ' + cls + '">' +
            '<div class="rev-q">' + (idx + 1) + '. ' + esc(it.question || it.text || '') +
            ' <span class="rev-tag ' + tagCls + '">' + esc(tag) + '</span></div>' +
            '<div class="rev-ans">Ҷавоби хонанда: <b>' + esc(it.studentAnswer != null ? it.studentAnswer : (it.selectedText || '—')) + '</b></div>' +
            '<div class="rev-ans">Ҷавоби дуруст: <b>' + esc(it.correctAnswer != null ? it.correctAnswer : (it.correctText || '—')) + '</b></div>' +
            (it.points != null ? '<div class="rev-ans">Хол: ' + esc(it.points) + (it.maxScore != null ? (' / ' + it.maxScore) : '') + '</div>' : '') +
            '</div>';
        }).join('');
      }
    } catch (e) {
      meta.textContent = '';
      body.innerHTML = '<p style="color:#b91c1c">Хато: ' + esc(e.message || e) +
        (e.status === 404 ? ' (Review API 404 — deploy-ро санҷед)' : '') + '</p>';
    }
  }

  function installResultsClickDelegation() {
    document.addEventListener('click', function (e) {
      var row = e.target && e.target.closest && e.target.closest('[data-attempt-id], tr[data-id], .result-row, .results-row');
      if (!row) return;
      var id = row.getAttribute('data-attempt-id') || row.getAttribute('data-id') || row.dataset.attemptId;
      if (!id) return;
      if (e.target.closest('button, a, input, select')) return;
      e.preventDefault();
      showReview(id, row.getAttribute('data-name') || '', row.getAttribute('data-title') || '');
    }, true);
  }

  function installStrongPatch() {
    if (typeof window.renderResults === 'function' && !window.renderResults.__revPatched) {
      var orig = window.renderResults;
      window.renderResults = function () {
        var r = orig.apply(this, arguments);
        try { bindResultRows(); } catch (e) {}
        return r;
      };
      window.renderResults.__revPatched = true;
    }
    bindResultRows();
  }

  function bindResultRows() {
    var nodes = document.querySelectorAll('#resultsTable tbody tr, #resultsBody tr, .results-list .result-row, [data-attempt-id]');
    nodes.forEach(function (tr) {
      if (tr.__revBound) return;
      tr.__revBound = true;
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', function (e) {
        if (e.target.closest('button, a, input, select')) return;
        var id = tr.getAttribute('data-attempt-id') || tr.getAttribute('data-id');
        if (!id) {
          var cells = tr.querySelectorAll('td');
          // try last cell hidden id
        }
        if (id) showReview(id, tr.getAttribute('data-name') || (tr.cells[0] && tr.cells[0].textContent) || '', '');
      });
    });
  }

  function boot() {
    injectStyles();
    ensureModal();
    installResultsClickDelegation();
    setTimeout(installStrongPatch, 300);
    setTimeout(installStrongPatch, 900);
    setTimeout(installStrongPatch, 2000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  window.__openAttemptReview = showReview;
  window.__closeAttemptReview = closeReview;
})();
