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
      let filename = fallbackName || 'Geografia_Export.xlsx';
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
    } catch (err) {
      console.error(err);
      if (hint) hint.textContent = 'Хато: ' + (err.message || err);
      alert('Export хато: ' + (err.message || err));
    }
  }

  let _allRows = [];
  let _previewTimer = null;

  function schedulePreview() {
    clearTimeout(_previewTimer);
    _previewTimer = setTimeout(updatePreview, 300);
  }

  function applyClientFilter() {
    // client-side filter already reflected in queryString for export;
    // table may be driven by admin.js — keep lightweight
  }

  async function updatePreview() {
    const hint = document.getElementById('exportPreviewHint');
    if (!hint) return;
    try {
      const res = await fetch('/api/admin/export/preview' + queryString(), {
        credentials: 'include',
        headers: authHeaders(),
      });
      if (!res.ok) {
        hint.textContent = '';
        return;
      }
      const data = await res.json();
      const n = data.results != null ? data.results : (data.count || 0);
      hint.textContent = n + ' сатр барои export';
    } catch (_) {
      hint.textContent = '';
    }
  }

  async function loadResultsForOlympiad(id) {
    // optional: admin.js may own the table
    schedulePreview();
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
      downloadExport('/api/admin/export/results' + queryString(), 'Geografia_Results.xlsx');
    });

    document.getElementById('btnExportOlympiad')?.addEventListener('click', () => {
      const id = (document.getElementById('resultOlympiadSelect') || {}).value;
      if (!id) {
        alert('Аввал олимпиадаро интихоб кунед');
        return;
      }
      downloadExport('/api/admin/export/olympiad/' + encodeURIComponent(id), 'Geografia_Olympiad_Results.xlsx');
    });

    document.getElementById('btnExportFull')?.addEventListener('click', () => {
      if (!confirm('Export пурраи платформа (Excel, 5 sheet). Давом?')) return;
      downloadExport('/api/admin/export/full', 'Geografia_Full_Export.xlsx');
    });

    document.getElementById('btnExportStudents')?.addEventListener('click', () => {
      downloadExport('/api/admin/export/students', 'Geografia_Students.xlsx');
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
