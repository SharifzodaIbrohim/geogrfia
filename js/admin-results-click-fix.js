/**
 * Results table click → open review modal.
 * Load AFTER admin-results-review.js. Safe if review JS missing.
 * No MutationObserver reload loop (that froze the Results tab).
 */
(function () {
  'use strict';

  var loading = false;
  var lastLoadedId = '';

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

  function fmtWhen(v) {
    if (!v) return '—';
    try {
      var d = new Date(v);
      if (isNaN(d.getTime())) return String(v).replace('T', ' ').slice(0, 19);
      var p = function (n) { return String(n).padStart(2, '0'); };
      return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' +
        p(d.getHours()) + ':' + p(d.getMinutes());
    } catch (e) {
      return String(v);
    }
  }

  function rowHtml(r) {
    var aid = r.id || r.attemptId || '';
    var name = r.studentName || r.name || r.fullName || '—';
    if (/^\d{10,}$/.test(String(name).trim())) name = '—';
    var sid = r.studentCode || r.studentId || r.student_code || '';
    if (sid && String(sid).indexOf('-') >= 0 && sid.length > 20) sid = '';
    var school = r.school || r.studentSchool || r.student_school || '';
    var cls = r.className || r.studentClass || r.student_class || '';
    var earned = r.earned != null ? r.earned : (r.pointsEarned != null ? r.pointsEarned : r.points);
    var totalMax = r.totalMax != null ? r.totalMax : (r.maxScore != null ? r.maxScore : r.totalPoints);
    var pct = r.score != null && r.score !== '' ? (String(r.score).indexOf('%') >= 0 ? String(r.score) : r.score + '%') : null;
    var points = '';
    if (earned != null && totalMax != null) points = earned + '/' + totalMax + ' хол';
    else if (r.correct != null && r.total != null) points = r.correct + '/' + r.total;
    var score = points && pct ? points + ' · ' + pct : (points || pct || '—');
    var st = statusLabel(r.status);
    var fin = fmtWhen(r.finishedAt || r.finished_at || r.submittedAt);
    return (
      '<tr class="result-row-clickable" data-attempt-id="' +
      esc(aid) +
      '" data-student-name="' +
      esc(name) +
      '" style="cursor:pointer" title="Клик → тафсилоти ҷавобҳо">' +
      '<td class="result-name-cell"><span class="result-name-link">' +
      esc(name) +
      '</span></td>' +
      '<td>' + esc(sid || '—') + '</td>' +
      '<td>' + esc(school || '—') + '</td>' +
      '<td>' + esc(cls || '—') + '</td>' +
      '<td>' + esc(score) + '</td>' +
      '<td>' + esc(st) + '</td>' +
      '<td>' + esc(fin) + '</td></tr>'
    );
  }

  async function loadResults(olympiadId, title, force) {
    var body = document.getElementById('resultsBody');
    if (!body) return;
    if (!olympiadId) {
      body.innerHTML = '';
      lastLoadedId = '';
      return;
    }
    if (loading) return;
    if (!force && lastLoadedId === String(olympiadId) && body.querySelector('tr[data-attempt-id]')) {
      return;
    }
    loading = true;
    body.innerHTML = '<tr><td colspan="7" class="muted">Боркунӣ…</td></tr>';
    try {
      var data = await api('/api/admin/olympiads/' + encodeURIComponent(olympiadId) + '/results');
      var rows = data.results || data.items || [];
      body.innerHTML = rows.length
        ? rows.map(rowHtml).join('')
        : '<tr><td colspan="7" class="muted">Холӣ</td></tr>';
      body.dataset.olympiadTitle = title || '';
      lastLoadedId = String(olympiadId);
    } catch (err) {
      body.innerHTML =
        '<tr><td colspan="7" class="muted">' + esc(err.message || err) + '</td></tr>';
    } finally {
      loading = false;
    }
  }

  function openReview(id, name, title) {
    if (typeof window.__openAttemptReview === 'function') {
      window.__openAttemptReview(id, name, title);
      return;
    }
    alert('Тафсилот бор нашудааст. Саҳифаро навсозӣ кунед.');
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
      loadResults(id, title, true);
    });

    function refresh() {
      if (!clone.value) return;
      loadResults(
        clone.value,
        (clone.options[clone.selectedIndex] && clone.options[clone.selectedIndex].text) || '',
        true
      );
    }

    var btnR = document.getElementById('btnRefreshResults');
    if (btnR) btnR.addEventListener('click', function (e) {
      e.preventDefault();
      refresh();
    });
    var btnL = document.getElementById('loadResultsBtn');
    if (btnL) btnL.addEventListener('click', function (e) {
      e.preventDefault();
      refresh();
    });

    if (clone.value) {
      setTimeout(function () {
        loadResults(
          clone.value,
          (clone.options[clone.selectedIndex] && clone.options[clone.selectedIndex].text) || '',
          true
        );
      }, 100);
    }
  }

  function boot() {
    installClick();
    setTimeout(installSelect, 400);
    setTimeout(function () {
      if (!window.__resultsClickFixInstalled) installSelect();
    }, 1500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
