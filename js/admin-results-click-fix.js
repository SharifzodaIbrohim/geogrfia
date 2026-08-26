/**
 * Results table click → open review modal.
 * Load AFTER admin-results-review.js. Safe if review JS missing.
 */
(function () {
  'use strict';

  function esc(s) {
    if (window.esc) return window.esc(s);
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function statusLabel(st) {
    if (window.statusLabel) return window.statusLabel(st);
    var s = String(st || '').toLowerCase();
    if (s === 'passed' || s === 'pass') return 'Гузашт';
    if (s === 'failed' || s === 'fail') return 'Нагузашт';
    if (s === 'timeout') return 'Вақт тамом';
    if (s === 'submitted') return 'Супорида шуд';
    return st || '—';
  }

  async function api(path, options) {
    options = options || {};
    if (typeof window.api === 'function') return window.api(path, options);
    var token = localStorage.getItem('geo_admin_token') || '';
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    if (token) headers['X-Admin-Token'] = token;
    var res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: 'include' }));
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function rowHtml(r) {
    var aid = r.id || r.attemptId || '';
    var name = r.studentName || r.name || r.fullName || r.studentId || '—';
    var school = r.school || r.studentSchool || '';
    var cls = r.className || r.studentClass || '';
    var score = r.score != null ? r.score + '%' : '—';
    var st = statusLabel(r.status);
    var fin = r.finishedAt || '';
    return (
      '<tr class="result-row-clickable" data-attempt-id="' +
      esc(aid) +
      '" data-student-name="' +
      esc(name) +
      '" style="cursor:pointer" title="Клик → тафсилоти ҷавобҳо">' +
      '<td class="result-name-cell"><span class="result-name-link">' +
      esc(name) +
      '</span></td>' +
      '<td>' +
      esc(school) +
      '</td><td>' +
      esc(cls) +
      '</td><td>' +
      esc(score) +
      '</td><td>' +
      esc(st) +
      '</td><td>' +
      esc(fin) +
      '</td></tr>'
    );
  }

  async function loadResults(olympiadId, title) {
    var body = document.getElementById('resultsBody');
    if (!body) return;
    if (!olympiadId) {
      body.innerHTML = '';
      return;
    }
    body.innerHTML = '<tr><td colspan="6" class="muted">Боркунӣ…</td></tr>';
    try {
      var data = await api('/api/admin/olympiads/' + encodeURIComponent(olympiadId) + '/results');
      var rows = data.results || data.items || [];
      body.innerHTML = rows.length
        ? rows.map(rowHtml).join('')
        : '<tr><td colspan="6" class="muted">Холӣ</td></tr>';
      body.dataset.olympiadTitle = title || '';
    } catch (err) {
      body.innerHTML =
        '<tr><td colspan="6" class="muted">' + esc(err.message || err) + '</td></tr>';
    }
  }

  function openReview(attemptId, name, title) {
    if (typeof window.__openAttemptReview === 'function') {
      window.__openAttemptReview(attemptId, name, title);
      return;
    }
    alert('Модули тафсилот ҳанӯз бор нашудааст. Саҳифаро навсозӣ кунед.');
  }

  function installClick() {
    var body = document.getElementById('resultsBody');
    if (!body || body.dataset.clickFix) return;
    body.dataset.clickFix = '1';
    body.addEventListener('click', function (e) {
      if (e.target.closest('button, a, input, select')) return;
      var tr = e.target.closest('tr[data-attempt-id]');
      if (!tr) return;
      var id = tr.getAttribute('data-attempt-id');
      if (!id) return;
      var name = tr.getAttribute('data-student-name') || '';
      var sel = document.getElementById('resultOlympiadSelect');
      var title =
        body.dataset.olympiadTitle ||
        (sel && sel.options[sel.selectedIndex] && sel.options[sel.selectedIndex].text) ||
        '';
      e.preventDefault();
      e.stopPropagation();
      openReview(id, name, title);
    });
  }

  function installSelect() {
    if (window.__resultsClickFixInstalled) return;
    var sel = document.getElementById('resultOlympiadSelect');
    if (!sel) return;
    window.__resultsClickFixInstalled = true;

    installClick();

    var parent = sel.parentNode;
    var clone = sel.cloneNode(true);
    clone.id = 'resultOlympiadSelect';
    parent.replaceChild(clone, sel);

    clone.addEventListener('change', function () {
      var id = clone.value;
      var title =
        (clone.options[clone.selectedIndex] && clone.options[clone.selectedIndex].text) || '';
      loadResults(id, title);
    });

    function refresh() {
      clone.dispatchEvent(new Event('change'));
    }

    var btnR = document.getElementById('btnRefreshResults');
    if (btnR) btnR.addEventListener('click', refresh);
    var btnL = document.getElementById('loadResultsBtn');
    if (btnL) btnL.addEventListener('click', refresh);

    if (clone.value) setTimeout(refresh, 80);

    var body = document.getElementById('resultsBody');
    if (body) {
      var obs = new MutationObserver(function () {
        var s = document.getElementById('resultOlympiadSelect');
        if (!s || !s.value) return;
        if (!document.querySelector('#resultsBody tr[data-attempt-id]')) {
          loadResults(s.value, (s.options[s.selectedIndex] && s.options[s.selectedIndex].text) || '');
        }
      });
      obs.observe(body, { childList: true, subtree: true });
    }
  }

  function boot() {
    installClick();
    setTimeout(installSelect, 250);
    setTimeout(installSelect, 800);
    setTimeout(installSelect, 1800);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
