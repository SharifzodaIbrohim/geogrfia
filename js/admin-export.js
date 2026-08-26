/**
 * Admin Export UI — search/filter + CSV/Excel download for Results tab.
 * Depends on admin.js (api, esc, statusLabel, displayName) when available.
 */
(function () {
  'use strict';

  function esc(s) {
    if (typeof window.esc === 'function') return window.esc(s);
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function statusLabel(st) {
    if (typeof window.statusLabel === 'function') return window.statusLabel(st);
    const s = String(st || '').toLowerCase();
    if (s === 'passed' || s === 'pass') return 'Гузашт';
    if (s === 'failed' || s === 'fail') return 'Нагузашт';
    if (s === 'timeout') return 'Вақт тамом';
    if (s === 'submitted') return 'Супорида шуд';
    return st || '—';
  }

  function displayName(r) {
    if (typeof window.displayName === 'function') return window.displayName(r);
    return r.studentName || r.fullName || r.name || r.studentId || '—';
  }

  function authHeaders() {
    const token = localStorage.getItem('geo_admin_token') || '';
    const h = {};
    if (token) h['X-Admin-Token'] = token;
    return h;
  }

  function getFilters() {
    const scoreRange = (document.getElementById('resultScoreRange') || {}).value || '';
    let scoreMin = '', scoreMax = '';
    if (scoreRange === '0-50') { scoreMin = '0'; scoreMax = '50'; }
    else if (scoreRange === '50-80') { scoreMin = '50'; scoreMax = '80'; }
    else if (scoreRange === '80-100') { scoreMin = '80'; scoreMax = '100'; }

    return {
      olympiadId: (document.getElementById('resultOlympiadSelect') || {}).value || '',
      school: (document.getElementById('resultSchoolFilter') || {}).value.trim() || '',
      className: (document.getElementById('resultClassFilter') || {}).value.trim() || '',
      status: (document.getElementById('resultStatusFilter') || {}).value || '',
      q: (document.getElementById('resultSearchQ') || {}).value.trim() || '',
      scoreMin,
      scoreMax,
    };
  }

  function queryString(extra) {
    const f = Object.assign({}, getFilters(), extra || {});
    const p = new URLSearchParams();
    Object.keys(f).forEach((k) => {
      if (f[k] !== '' && f[k] != null) p.set(k, f[k]);
    });
    const s = p.toString();
    return s ? '?' + s : '';
  }

  async function downloadExport(path, fallbackName) {
    const hint = document.getElementById('exportPreviewHint');
    if (hint) hint.textContent = 'Боргирӣ…';
    try {
      const res = await fetch(path, {
        method: 'GET',
        credentials: 'include',
        headers: authHeaders(),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || ('Хато ' + res.status));
      }
      const blob = await res.blob();
      let filename = fallbackName || 'Geografia_Export.csv';
      const cd = res.headers.get('Content-Disposition') || '';
      const m = /filename="?([^";]+)"?/i.exec(cd);
      if (m) filename = m[1];
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      if (hint) hint.textContent = 'Боргирӣ шуд: ' + filename;
    } catch (e) {
      alert('Export: ' + (e.message || e));
      if (hint) hint.textContent = '';
    }
  }

  let previewTimer = null;
  async function updatePreview() {
    const hint = document.getElementById('exportPreviewHint');
    if (!hint) return;
    try {
      const res = await fetch('/api/admin/export/preview' + queryString(), {
        credentials: 'include',
        headers: authHeaders(),
      });
      if (!res.ok) return;
      const data = await res.json();
      const n = data.results ?? 0;
      hint.textContent = n + ' сатр экспорт мешавад';
    } catch (_) {}
  }

  function schedulePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(updatePreview, 350);
  }

  let _allRows = [];

  function applyClientFilter() {
    const body = document.getElementById('resultsBody');
    if (!body) return;
    const f = getFilters();
    const q = (f.q || '').toLowerCase();
    const school = (f.school || '').toLowerCase();
    const cls = (f.className || '').toLowerCase();
    const status = (f.status || '').toLowerCase();
    let smin = null, smax = null;
    if (f.scoreMin !== '') smin = parseFloat(f.scoreMin);
    if (f.scoreMax !== '') smax = parseFloat(f.scoreMax);

    const filtered = _allRows.filter((r) => {
      if (school && !(String(r.school || '').toLowerCase().includes(school))) return false;
      if (cls && !(String(r.className || '').toLowerCase().includes(cls))) return false;
      if (status) {
        const st = String(r.status || '').toLowerCase();
        if (status === 'passed' && st !== 'passed' && st !== 'pass') return false;
        if (status === 'failed' && st !== 'failed' && st !== 'fail') return false;
        if (status === 'timeout' && st !== 'timeout') return false;
      }
      const sc = r.score != null ? Number(r.score) : null;
      if (smin != null && (sc == null || sc < smin)) return false;
      if (smax != null && (sc == null || sc > smax)) return false;
      if (q) {
        const blob = [
          r.studentName, r.fullName, r.name, r.studentId, r.school, r.className,
        ].map((x) => String(x || '').toLowerCase()).join(' ');
        if (!blob.includes(q)) return false;
      }
      return true;
    });

    renderRows(filtered);
    const hint = document.getElementById('exportPreviewHint');
    if (hint) hint.textContent = filtered.length + ' сатр (филтршуда)';
  }

  function renderRows(rows) {
    const body = document.getElementById('resultsBody');
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="7" class="muted">Холӣ</td></tr>';
      return;
    }
    body.innerHTML = rows.map((r) => {
      const name = displayName(r);
      const sid = r.studentId || r.student_code || '';
      const school = r.school || r.studentSchool || '';
      const cls = r.className || '';
      const score = r.score != null ? r.score + '%' : '—';
      const st = statusLabel(r.status);
      const when = (r.finishedAt || r.finished_at || '').toString().replace('T', ' ').slice(0, 19);
      const aid = r.attemptId || r.id || '';
      return `<tr data-attempt-id="${esc(aid)}" style="cursor:pointer">
        <td>${esc(name)}</td>
        <td><code>${esc(sid)}</code></td>
        <td>${esc(school)}</td>
        <td>${esc(cls)}</td>
        <td>${esc(score)}</td>
        <td>${esc(st)}</td>
        <td>${esc(when)}</td>
      </tr>`;
    }).join('');
  }

  async function loadResultsForOlympiad(olympiadId) {
    const body = document.getElementById('resultsBody');
    if (!body) return;
    if (!olympiadId) {
      _allRows = [];
      body.innerHTML = '<tr><td colspan="7" class="muted">Олимпиадаро интихоб кунед</td></tr>';
      schedulePreview();
      return;
    }
    body.innerHTML = '<tr><td colspan="7" class="muted">Боркунӣ…</td></tr>';
    try {
      let data;
      if (typeof window.api === 'function') {
        data = await window.api('/api/admin/olympiads/' + encodeURIComponent(olympiadId) + '/results');
      } else {
        const res = await fetch('/api/admin/olympiads/' + encodeURIComponent(olympiadId) + '/results', {
          credentials: 'include',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeaders()),
        });
        data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Хато');
      }
      _allRows = data.results || data.items || [];
      applyClientFilter();
    } catch (err) {
      body.innerHTML = '<tr><td colspan="7" class="muted">Хато: ' + esc(err.message || err) + '</td></tr>';
      _allRows = [];
    }
  }

  function bind() {
    const sel = document.getElementById('resultOlympiadSelect');
    if (sel) {
      sel.addEventListener('change', () => {
        loadResultsForOlympiad(sel.value);
        schedulePreview();
      });
    }

    ['resultSchoolFilter', 'resultClassFilter', 'resultStatusFilter', 'resultScoreRange', 'resultSearchQ']
      .forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        const ev = id === 'resultSearchQ' ? 'input' : 'change';
        el.addEventListener(ev, () => {
          applyClientFilter();
          schedulePreview();
        });
        if (id === 'resultSearchQ') el.addEventListener('search', () => {
          applyClientFilter();
          schedulePreview();
        });
      });

    document.getElementById('btnRefreshResults')?.addEventListener('click', () => {
      const id = (document.getElementById('resultOlympiadSelect') || {}).value;
      loadResultsForOlympiad(id);
      schedulePreview();
    });

    document.getElementById('btnExportFiltered')?.addEventListener('click', () => {
      downloadExport('/api/admin/export/results' + queryString(), 'Geografia_Results.csv');
    });

    document.getElementById('btnExportOlympiad')?.addEventListener('click', () => {
      const id = (document.getElementById('resultOlympiadSelect') || {}).value;
      if (!id) {
        alert('Аввал олимпиадаро интихоб кунед');
        return;
      }
      downloadExport('/api/admin/export/olympiad/' + encodeURIComponent(id), 'Geografia_Olympiad_Results.csv');
    });

    document.getElementById('btnExportFull')?.addEventListener('click', () => {
      if (!confirm('Export пурраи платформа (Excel, 5 sheet). Давом?')) return;
      downloadExport('/api/admin/export/full', 'Geografia_Full_Export.xlsx');
    });

    document.getElementById('btnExportStudents')?.addEventListener('click', () => {
      downloadExport('/api/admin/export/students', 'Geografia_Students.csv');
    });

    document.querySelectorAll('.tab[data-tab="results"]').forEach((btn) => {
      btn.addEventListener('click', () => setTimeout(schedulePreview, 200));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }

  window.__geoExport = {
    getFilters,
    loadResultsForOlympiad,
    updatePreview,
    applyClientFilter,
  };
})();
