/** Admin fixes: LB save, clear recent (real delete), filter Gmail from ID results */
(() => {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (tok()) headers['X-Admin-Token'] = tok();
    const res = await fetch(path, { ...opts, headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }
  function isGmail(r) {
    const id = String(r.studentId || r.studentCode || '');
    const name = String(r.studentName || '');
    return id.startsWith('g:') || id.startsWith('gmail:') || /^gmail/i.test(name);
  }
  function displayName(r) {
    let n = String(r.studentName || '').trim();
    if (!n || /^gmail/i.test(n)) n = r.email || r.userEmail || 'Иштирокчӣ';
    return n;
  }

  async function doClearRecent() {
    if (!confirm('Натиҷаҳои охирин (то 30) аз база пок шаванд? Ин бебозгашт аст.')) return;
    try {
      try {
        await api('/api/admin/monitor/clear-recent', { method: 'POST', body: '{}' });
      } catch (_) {
        await api('/api/admin/results/clear-recent', { method: 'POST', body: '{}' });
      }
      const body = document.getElementById('recentResultsBody');
      if (body) body.innerHTML = '<tr><td colspan="6">Пок шуд</td></tr>';
      if (typeof window.loadMonitor === 'function') {
        window.loadMonitor();
      } else {
        const refresh = document.getElementById('refreshLiveBtn');
        if (refresh) refresh.click();
      }
    } catch (e) {
      alert(e.message || 'Пок карда нашуд');
    }
  }

  function wire() {
    // Нигоҳ доштан Leaderboard public
    const saveLb = document.getElementById('saveLbVisBtn');
    if (saveLb && !saveLb._fixed) {
      saveLb._fixed = true;
      saveLb.addEventListener('click', async () => {
        const id = document.getElementById('resultOlympiadSelect')?.value;
        if (!id) { alert('Аввал олимпиадаро интихоб кунед'); return; }
        const isPublic = document.getElementById('leaderboardPublicChk')?.checked !== false;
        try {
          await api('/api/admin/olympiads/' + id + '/leaderboard', {
            method: 'PATCH',
            body: JSON.stringify({ public: isPublic }),
          });
          alert('Сабт шуд: Leaderboard ' + (isPublic ? 'оммавӣ' : 'пӯшида'));
        } catch (e) {
          alert(e.message);
        }
      });
    }

    const loadLb = document.getElementById('loadLeaderboardBtn');
    if (loadLb && !loadLb._fixed) {
      loadLb._fixed = true;
      loadLb.addEventListener('click', async () => {
        const id = document.getElementById('resultOlympiadSelect')?.value;
        const body = document.getElementById('leaderboardBody');
        if (!id) { alert('Аввал олимпиадаро интихоб кунед'); return; }
        try {
          const data = await api('/api/admin/olympiads/' + id + '/leaderboard');
          const rows = (data.entries || data.leaderboard || []).filter((r) => !isGmail(r));
          if (data.leaderboardPublic != null && document.getElementById('leaderboardPublicChk')) {
            document.getElementById('leaderboardPublicChk').checked = !!data.leaderboardPublic;
          }
          body.innerHTML = rows.length
            ? rows.map((r, i) => `<tr><td>${r.rank || i + 1}</td><td>${displayName(r)}</td><td>${r.studentClass || ''}</td><td>${r.studentSchool || ''}</td><td><b>${r.score ?? '—'}%</b></td><td>${r.status || ''}</td></tr>`).join('')
            : '<tr><td colspan="6">Холӣ</td></tr>';
        } catch (e) {
          body.innerHTML = `<tr><td colspan="6">${e.message}</td></tr>`;
        }
      });
    }

    // Пок кардан recent — real delete (top 30 finished)
    ['clearRecentResultsBtn', 'clearRecentBtn', 'btnClearRecent'].forEach((id) => {
      const el = document.getElementById(id);
      if (el && !el._fixed) {
        el._fixed = true;
        el.addEventListener('click', (ev) => {
          ev.preventDefault();
          doClearRecent();
        });
      }
    });
    let clearBtn = document.getElementById('clearRecentResultsBtn');
    if (!clearBtn) {
      const h3s = [...document.querySelectorAll('h3')].filter((h) => h.textContent.includes('Натиҷаҳои охирин'));
      if (h3s[0]) {
        clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn small';
        clearBtn.id = 'clearRecentResultsBtn';
        clearBtn.textContent = 'Пок кардан';
        clearBtn.style.marginLeft = '0.5rem';
        h3s[0].appendChild(clearBtn);
        clearBtn._fixed = true;
        clearBtn.addEventListener('click', (ev) => {
          ev.preventDefault();
          doClearRecent();
        });
      }
    }

    // Clear all results button
    let clearAll = document.getElementById('clearAllResultsBtn');
    if (!clearAll) {
      const save = document.getElementById('saveLbVisBtn');
      if (save && save.parentElement) {
        clearAll = document.createElement('button');
        clearAll.type = 'button';
        clearAll.className = 'btn danger';
        clearAll.id = 'clearAllResultsBtn';
        clearAll.textContent = 'Пок кардани ҳама натиҷаҳо';
        save.parentElement.appendChild(clearAll);
      }
    }
    if (clearAll && !clearAll._fixed) {
      clearAll._fixed = true;
      clearAll.addEventListener('click', async () => {
        if (!confirm('ҲАМА натиҷаҳо нест шаванд? Бебозгашт!')) return;
        try {
          await api('/api/admin/results/clear-all', { method: 'POST', body: '{}' });
          alert('Пок шуд');
          const rb = document.getElementById('resultsBody');
          if (rb) rb.innerHTML = '';
          const rcb = document.getElementById('recentResultsBody');
          if (rcb) rcb.innerHTML = '<tr><td colspan="6">Холӣ</td></tr>';
        } catch (e) {
          alert(e.message);
        }
      });
    }

    // Filter Gmail names from recent results table (MutationObserver)
    const recent = document.getElementById('recentResultsBody');
    if (recent && !recent._obs) {
      recent._obs = new MutationObserver(() => {
        [...recent.querySelectorAll('tr')].forEach((tr) => {
          const t = tr.textContent || '';
          if (/gmail/i.test(t) || t.includes('g:')) tr.remove();
        });
      });
      recent._obs.observe(recent, { childList: true, subtree: true });
    }

    // Note under results
    const resultsTab = document.getElementById('tab-results');
    if (resultsTab && !document.getElementById('resultsGmailNote')) {
      const note = document.createElement('p');
      note.id = 'resultsGmailNote';
      note.className = 'muted';
      note.textContent = 'Ин ҷо танҳо хонандагони ID. Натиҷаҳои Gmail → «Gmail корбарон».';
      const h2 = resultsTab.querySelector('h2');
      if (h2) h2.after(note);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(wire, 300));
  else setTimeout(wire, 300);
})();
