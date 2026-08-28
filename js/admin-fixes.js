/** Admin fixes: LB save, clear recent (real delete), filter Gmail from ID results */
(() => {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    const t = tok();
    if (t) headers['X-Admin-Token'] = t;
    const res = await fetch(path, { ...opts, headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }
  function isGmailUser(r) {
    const id = String(r.studentId || r.code || r.id || '');
    const name = String(r.studentName || r.name || r.fullName || '');
    if (/gmail|@/.test(name.toLowerCase())) return true;
    if (/^g_/i.test(id)) return true;
    return false;
  }
  const origLoadResults = window.loadResultsIntoBody;
  // Filter Gmail from ID-based results if helper exists
  document.addEventListener('DOMContentLoaded', () => {
    try {
      const btn = document.getElementById('clearRecentResultsBtn') || document.getElementById('clearRecentBtn');
      if (btn && !btn.dataset.fixed) {
        btn.dataset.fixed = '1';
        btn.addEventListener('click', async (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (!confirm('Натиҷаҳои охиринро пок кунем?')) return;
          try {
            try { await api('/api/admin/monitor/clear-recent', { method: 'POST', body: '{}' }); }
            catch (_) { await api('/api/admin/results/clear-recent', { method: 'POST', body: '{}' }); }
            if (typeof window.loadMonitor === 'function') window.loadMonitor();
          } catch (err) { alert(err.message || 'Пок нашуд'); }
        }, true);
      }
    } catch (_) {}
  });
})();

/** Display-only: format monitor/results scores as points + percent. Does not change scoring. */
(function () {
  'use strict';
  function formatScoreCell(r) {
    if (!r) return '—';
    var earned = r.earned != null ? r.earned : (r.pointsEarned != null ? r.pointsEarned : r.points);
    var totalMax = r.totalMax != null ? r.totalMax : (r.maxScore != null ? r.maxScore : r.totalPoints);
    var pct = null;
    if (r.score != null && r.score !== '') {
      pct = String(r.score).indexOf('%') >= 0 ? String(r.score) : (r.score + '%');
    }
    var points = '';
    if (earned != null && totalMax != null) points = earned + '/' + totalMax + ' хол';
    else if (r.correct != null && r.total != null) points = r.correct + '/' + r.total;
    if (points && pct) return points + ' · ' + pct;
    if (points) return points;
    if (pct) return pct;
    return '—';
  }
  window.formatScoreCell = formatScoreCell;

  function patchRecentTable(rows) {
    var body = document.getElementById('recentResultsBody');
    if (!body || !rows || !rows.length) return;
    var trs = body.querySelectorAll('tr');
    if (trs.length !== rows.length) return;
    rows.forEach(function (r, i) {
      var tds = trs[i].querySelectorAll('td');
      if (tds.length >= 4) tds[3].textContent = formatScoreCell(r);
    });
  }

  var _fetch = window.fetch;
  window.fetch = function (input, init) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var p = _fetch.apply(this, arguments);
    if (String(url).indexOf('/api/admin/monitor') >= 0) {
      return p.then(function (res) {
        var clone = res.clone();
        clone.json().then(function (data) {
          try {
            var rows = data.recentResults || data.results || [];
            setTimeout(function () { patchRecentTable(rows); }, 50);
            setTimeout(function () { patchRecentTable(rows); }, 300);
          } catch (e) {}
        }).catch(function () {});
        return res;
      });
    }
    return p;
  };
})();
