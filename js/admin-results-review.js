/**
 * Admin Results Review — click student row → full answer detail + print.
 * Depends on admin.js (api, esc, displayName, statusLabel, token).
 * Table reload handled by admin-results-click-fix.js (no MutationObserver here).
 */
(function () {
  'use strict';

  const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  function esc(s) {
    if (window.esc) return window.esc(s);
    return String(s ?? '')
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>')
      .replace(/"/g, '"');
  }

  function statusLabel(st) {
    if (window.statusLabel) return window.statusLabel(st);
    const s = String(st || '').toLowerCase();
    if (s === 'passed' || s === 'pass') return 'Гузашт';
    if (s === 'failed' || s === 'fail') return 'Нагузашт';
    if (s === 'timeout') return 'Вақт тамом';
    if (s === 'submitted') return 'Супорида шуд';
    return st || '—';
  }

  async function api(path, options = {}) {
    if (typeof window.api === 'function') return window.api(path, options);
    const token = localStorage.getItem('geo_admin_token') || '';
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['X-Admin-Token'] = token;
    const res = await fetch(path, { ...options, headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function ensureModal() {
    let el = document.getElementById('reviewModal');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'reviewModal';
    el.className = 'review-modal hidden';
    el.innerHTML = `
      <div class="review-modal-backdrop" data-review-close></div>
      <div class="review-modal-panel" role="dialog" aria-modal="true">
        <div class="review-modal-toolbar no-print">
          <h2 id="reviewModalTitle">Тафсилоти ҷавобҳо</h2>
          <div class="review-modal-actions">
            <button type="button" class="btn primary" id="reviewPrintBtn">🖨 Чоп кардан</button>
            <button type="button" class="btn" data-review-close>Пӯшидан</button>
          </div>
        </div>
        <div class="review-modal-body" id="reviewModalBody">
          <div class="muted center" style="padding:2rem">Боркунӣ…</div>
        </div>
      </div>`;
    document.body.appendChild(el);
    el.querySelectorAll('[data-review-close]').forEach((b) => {
      b.addEventListener('click', closeReview);
    });
    document.getElementById('reviewPrintBtn')?.addEventListener('click', printReview);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !el.classList.contains('hidden')) closeReview();
    });
    return el;
  }

  function openReview() {
    const el = ensureModal();
    el.classList.remove('hidden');
    document.body.classList.add('review-open');
  }

  function closeReview() {
    const el = document.getElementById('reviewModal');
    if (el) el.classList.add('hidden');
    document.body.classList.remove('review-open');
  }

  function renderOptionLine(opt) {
    const letter = esc(opt.letter || '');
    const text = esc(opt.text || '');
    let cls = 'rev-opt';
    let marks = '';
    if (opt.isCorrect && opt.studentSelected) {
      cls += ' rev-opt-both';
      marks = ' <span class="rev-tag rev-tag-ok">← Ҷавоби дуруст + Ҷавоби хонанда</span>';
    } else if (opt.isCorrect) {
      cls += ' rev-opt-correct';
      marks = ' <span class="rev-tag rev-tag-ok">← Ҷавоби дуруст</span>';
    } else if (opt.studentSelected) {
      cls += ' rev-opt-student';
      marks = ' <span class="rev-tag rev-tag-bad">← Ҷавоби хонанда</span>';
    }
    return `<div class="${cls}"><strong>${letter}.</strong> ${text}${marks}</div>`;
  }

  function renderItem(item) {
    const num = item.number;
    const qtext = esc(item.text || '');
    const type = String(item.type || 'single').toLowerCase();
    let body = '';

    if (['short', 'text', 'number', 'numeric', 'open', 'essay', 'written'].includes(type)) {
      body = `
        <div class="rev-kv"><span class="rev-k">Ҷавоби дуруст:</span>
          <span class="rev-correct">${esc(item.correctAnswer ?? item.correctText ?? '—')}</span></div>
        <div class="rev-kv"><span class="rev-k">Ҷавоби хонанда:</span>
          <span class="${item.isCorrect ? 'rev-correct' : 'rev-wrong'}">${esc(item.studentAnswer ?? '—')}</span></div>`;
    } else if (['matching', 'match'].includes(type)) {
      body = `
        <div class="rev-kv"><span class="rev-k">Ҷуфтҳои дуруст:</span>
          <pre class="rev-pre">${esc(
            typeof item.correctAnswer === 'object'
              ? JSON.stringify(item.correctAnswer, null, 2)
              : (item.correctAnswer ?? '—')
          )}</pre></div>
        <div class="rev-kv"><span class="rev-k">Ҷавоби хонанда:</span>
          <pre class="rev-pre ${item.isCorrect ? 'rev-correct' : 'rev-wrong'}">${esc(
            item.studentAnswer ?? '—'
          )}</pre></div>`;
    } else {
      const opts = (item.options || []).map(renderOptionLine).join('') ||
        `<div class="muted">Вариантҳо нест</div>`;
      body = `<div class="rev-options">${opts}</div>`;
      if (!item.options?.length && item.correctText) {
        body += `<div class="rev-kv"><span class="rev-k">Дуруст:</span>
          <span class="rev-correct">${esc(item.correctText)}</span></div>`;
      }
      if (!item.options?.length && item.studentAnswer) {
        body += `<div class="rev-kv"><span class="rev-k">Хонанда:</span>
          <span class="${item.isCorrect ? 'rev-correct' : 'rev-wrong'}">${esc(item.studentAnswer)}</span></div>`;
      }
    }

    const resultCls = item.isBlank
      ? 'rev-result-blank'
      : item.isCorrect
        ? 'rev-result-ok'
        : 'rev-result-bad';
    const pointsTxt = item.isCorrect
      ? `+${item.points ?? 1} хол`
      : `0 хол`;

    return `
      <article class="rev-item ${item.isCorrect ? 'is-ok' : item.isBlank ? 'is-blank' : 'is-bad'}">
        <header class="rev-item-h">
          <span class="rev-num">Саволи ${num}</span>
          <span class="rev-type">${esc(type)}</span>
        </header>
        <div class="rev-qtext">${qtext}</div>
        ${body}
        <div class="rev-result ${resultCls}">
          Натиҷа: <strong>${esc(item.resultLabel || '')}</strong>
          (${pointsTxt})
        </div>
      </article>`;
  }

  function renderReview(data) {
    const st = data.student || {};
    const stats = data.stats || {};
    const pct = data.total ? Math.round(((data.correct ?? stats.correct ?? 0) / data.total) * 100) : (data.score ?? 0);
    const scoreLine = `${data.correct ?? stats.correct ?? 0}/${data.total ?? 0} = ${data.score ?? pct}%`;
    const statusTxt = statusLabel(data.status);
    const statusCls = String(data.status || '').toLowerCase().includes('pass') ? 'rev-badge-ok' : 'rev-badge-bad';

    const header = `
      <div class="rev-print-header only-print">
        <div class="rev-brand">Geografia</div>
        <div class="rev-doc-title">Варақаи тафсилоти ҷавобҳо</div>
      </div>
      <div class="rev-summary">
        <div class="rev-sum-grid">
          <div><span class="rev-k">Хонанда</span><div class="rev-v">${esc(st.name || '—')}</div></div>
          <div><span class="rev-k">Мактаб</span><div class="rev-v">${esc(st.school || '—')}</div></div>
          <div><span class="rev-k">Синф</span><div class="rev-v">${esc(st.className || '—')}</div></div>
          <div><span class="rev-k">Олимпиада</span><div class="rev-v">${esc(data.olympiadTitle || '—')}</div></div>
          <div><span class="rev-k">Хол</span><div class="rev-v rev-score">${esc(scoreLine)}</div></div>
          <div><span class="rev-k">Статус</span><div class="rev-v"><span class="rev-badge ${statusCls}">${esc(statusTxt)}</span></div></div>
          <div><span class="rev-k">Вақти супоридан</span><div class="rev-v">${esc(data.finishedAt || '—')}</div></div>
          <div><span class="rev-k">Дуруст / Нодуруст / Беҷавоб</span>
            <div class="rev-v">${stats.correct ?? 0} / ${stats.wrong ?? 0} / ${stats.blank ?? 0}</div></div>
        </div>
        ${data.message ? `<p class="rev-warn muted">${esc(data.message)}</p>` : ''}
      </div>`;

    const items = (data.items || []).map(renderItem).join('') ||
      '<p class="muted">Саволҳо ёфт нашуданд.</p>';

    const footer = `
      <div class="rev-print-footer only-print">
        <span>Санаи чоп: ${esc(new Date().toLocaleString('tg-TJ'))}</span>
        <span>Geografia Platform</span>
      </div>`;

    return header + `<div class="rev-list">${items}</div>` + footer;
  }

  function printReview() {
    const modal = document.getElementById('reviewModal');
    if (!modal) return;
    window.print();
  }

  async function showReview(attemptId, fallbackName, olympiadTitle) {
    if (!attemptId) {
      alert('Attempt ID нест');
      return;
    }
    const modal = ensureModal();
    const body = document.getElementById('reviewModalBody');
    const title = document.getElementById('reviewModalTitle');
    title.textContent = `Тафсилоти ҷавобҳо — ${fallbackName || '…'} — ${olympiadTitle || ''}`;
    body.innerHTML = '<div class="muted center" style="padding:2rem">Боркунӣ…</div>';
    openReview();
    try {
      const data = await api('/api/admin/attempts/' + encodeURIComponent(attemptId) + '/review');
      const name = (data.student && data.student.name) || fallbackName || '';
      const ot = data.olympiadTitle || olympiadTitle || '';
      title.textContent = `Тафсилоти ҷавобҳо — ${name} — ${ot}`;
      body.innerHTML = renderReview(data);
      body.dataset.attemptId = attemptId;
    } catch (err) {
      body.innerHTML = `<div class="rev-error">
        <p><strong>Бор карда нашуд</strong></p>
        <p class="muted">${esc(err.message || err)}</p>
        <p class="muted">Агар attempt қадим бошад, ҷавобҳои муфассал метавонанд мавҷуд набошанд.</p>
      </div>`;
    }
  }

  function installResultsClickDelegation() {
    const body = document.getElementById('resultsBody');
    if (!body || body.dataset.reviewClick) return;
    body.dataset.reviewClick = '1';
    body.addEventListener('click', (e) => {
      if (e.target.closest('button, a, input, select')) return;
      const tr = e.target.closest('tr[data-attempt-id]');
      if (!tr) return;
      const id = tr.getAttribute('data-attempt-id');
      if (!id) return;
      const name = tr.getAttribute('data-student-name') || '';
      const sel = document.getElementById('resultOlympiadSelect');
      const title =
        body.dataset.olympiadTitle ||
        (sel && sel.options[sel.selectedIndex] && sel.options[sel.selectedIndex].text) ||
        '';
      e.preventDefault();
      e.stopPropagation();
      showReview(id, name, title);
    });
  }

  function installStrongPatch() {
    if (window.__reviewPatchInstalled) return;
    window.__reviewPatchInstalled = true;
    installResultsClickDelegation();
  }

  function injectStyles() {
    if (document.getElementById('reviewModalStyles')) return;
    const style = document.createElement('style');
    style.id = 'reviewModalStyles';
    style.textContent = `
.result-row-clickable:hover { background: var(--accent-dim, rgba(112,219,151,.12)); }
.result-name-link { color: var(--accent, #70db97); text-decoration: underline; text-underline-offset: 2px; font-weight: 600; }
.review-modal {
  position: fixed; inset: 0; z-index: 9999;
  display: flex; align-items: stretch; justify-content: center;
}
.review-modal.hidden { display: none !important; }
.review-modal-backdrop {
  position: absolute; inset: 0; background: rgba(0,0,0,.55);
}
.review-modal-panel {
  position: relative; z-index: 1;
  width: min(920px, 100%);
  margin: 12px; max-height: calc(100vh - 24px);
  background: var(--surface, #1c211c);
  border: 1px solid var(--border, rgba(255,255,255,.1));
  border-radius: 16px;
  display: flex; flex-direction: column;
  box-shadow: 0 16px 48px rgba(0,0,0,.45);
  overflow: hidden;
}
.review-modal-toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 14px 18px; border-bottom: 1px solid var(--border, rgba(255,255,255,.1));
  flex-shrink: 0; background: var(--surface-2, #262c26);
}
.review-modal-toolbar h2 { margin: 0; font-size: 1.05rem; font-weight: 650; }
.review-modal-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.review-modal-body {
  overflow: auto; padding: 18px 20px 28px; flex: 1;
}
.rev-summary {
  background: var(--surface-2, #262c26);
  border: 1px solid var(--border, rgba(255,255,255,.08));
  border-radius: 12px; padding: 14px 16px; margin-bottom: 18px;
}
.rev-sum-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px;
}
.rev-k { display: block; font-size: .75rem; color: var(--muted, #9aa39a); margin-bottom: 2px; }
.rev-v { font-weight: 600; }
.rev-score { color: var(--accent, #70db97); font-size: 1.1rem; }
.rev-badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .85rem;
}
.rev-badge-ok { background: rgba(112,219,151,.2); color: #70db97; }
.rev-badge-bad { background: rgba(248,113,113,.18); color: #f87171; }
.rev-warn { margin: 10px 0 0; font-size: .9rem; }
.rev-item {
  border: 1px solid var(--border, rgba(255,255,255,.08));
  border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
  background: var(--bg, #121512);
}
.rev-item.is-ok { border-left: 4px solid #70db97; }
.rev-item.is-bad { border-left: 4px solid #f87171; }
.rev-item.is-blank { border-left: 4px solid #9aa39a; }
.rev-item-h { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 6px; }
.rev-num { font-weight: 700; color: var(--accent, #70db97); }
.rev-type { font-size: .75rem; color: var(--muted); text-transform: uppercase; }
.rev-qtext { font-size: 1.02rem; margin-bottom: 10px; line-height: 1.4; }
.rev-options { display: grid; gap: 4px; margin-bottom: 8px; }
.rev-opt { padding: 6px 10px; border-radius: 8px; background: rgba(255,255,255,.03); }
.rev-opt-correct { background: rgba(112,219,151,.15); color: #a7f3c0; }
.rev-opt-student { background: rgba(248,113,113,.15); color: #fecaca; }
.rev-opt-both { background: rgba(112,219,151,.22); color: #a7f3c0; }
.rev-tag { font-size: .8rem; font-weight: 600; white-space: nowrap; }
.rev-tag-ok { color: #70db97; }
.rev-tag-bad { color: #f87171; }
.rev-kv { margin: 4px 0; }
.rev-correct { color: #70db97; font-weight: 600; }
.rev-wrong { color: #f87171; font-weight: 600; }
.rev-pre {
  margin: 4px 0; padding: 8px; border-radius: 8px;
  background: rgba(0,0,0,.25); white-space: pre-wrap; font-size: .9rem;
}
.rev-result { margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--border); font-size: .95rem; }
.rev-result-ok { color: #70db97; }
.rev-result-bad { color: #f87171; }
.rev-result-blank { color: #9aa39a; }
.rev-error { text-align: center; padding: 2rem; }
.only-print { display: none; }
.rev-print-header { text-align: center; margin-bottom: 16px; }
.rev-brand { font-size: 1.4rem; font-weight: 800; letter-spacing: .04em; }
.rev-doc-title { font-size: 1.1rem; margin-top: 4px; }
.rev-print-footer {
  margin-top: 24px; padding-top: 12px; border-top: 1px solid #ccc;
  display: flex; justify-content: space-between; font-size: .85rem; color: #555;
}

@media print {
  @page { size: A4; margin: 12mm; }
  html, body {
    background: #fff !important;
    color: #111 !important;
    height: auto !important;
    overflow: visible !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  body * { visibility: hidden !important; }
  #reviewModal, #reviewModal * { visibility: visible !important; }
  #reviewModal {
    position: absolute !important;
    left: 0 !important;
    top: 0 !important;
    right: 0 !important;
    width: 100% !important;
    height: auto !important;
    display: block !important;
    inset: auto !important;
    background: #fff !important;
    z-index: 1 !important;
  }
  .review-modal-backdrop,
  .no-print,
  .review-modal-toolbar {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    background: transparent !important;
    opacity: 0 !important;
  }
  .review-modal-panel {
    position: static !important;
    width: 100% !important;
    max-height: none !important;
    margin: 0 !important;
    border: none !important;
    box-shadow: none !important;
    background: #fff !important;
    color: #111 !important;
    border-radius: 0 !important;
    overflow: visible !important;
  }
  .review-modal-body {
    overflow: visible !important;
    padding: 0 !important;
    color: #111 !important;
  }
  .only-print { display: block !important; }
  .rev-print-header {
    display: block !important;
    text-align: center;
    margin: 0 0 14px 0 !important;
    padding: 0 !important;
    background: transparent !important;
    color: #111 !important;
  }
  .rev-brand { color: #111 !important; }
  .rev-doc-title { color: #333 !important; }
  .rev-summary, .rev-item {
    background: #fff !important;
    border-color: #ccc !important;
    color: #111 !important;
    break-inside: avoid;
  }
  .rev-opt { background: #f7f7f7 !important; color: #111 !important; }
  .rev-opt-correct, .rev-opt-both { background: #e6f7ed !important; color: #065f3c !important; }
  .rev-opt-student { background: #fde8e8 !important; color: #9b1c1c !important; }
  .rev-correct, .rev-tag-ok, .rev-result-ok, .rev-num, .rev-score { color: #065f3c !important; }
  .rev-wrong, .rev-tag-bad, .rev-result-bad { color: #9b1c1c !important; }
  .rev-badge-ok { background: #e6f7ed !important; color: #065f3c !important; }
  .rev-badge-bad { background: #fde8e8 !important; color: #9b1c1c !important; }
  .rev-k, .rev-type { color: #555 !important; }
  .rev-pre { background: #f3f3f3 !important; color: #111 !important; }
  a { text-decoration: none !important; color: inherit !important; }
}
`;
    document.head.appendChild(style);
  }

  function boot() {
    injectStyles();
    ensureModal();
    installResultsClickDelegation();
    setTimeout(installStrongPatch, 300);
    setTimeout(installStrongPatch, 900);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  window.__openAttemptReview = showReview;
  window.__closeAttemptReview = closeReview;
})();
