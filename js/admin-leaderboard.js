(() => {
  const tokenKey = 'geo_admin_token';
  function token() {
    return localStorage.getItem(tokenKey) || localStorage.getItem('adminToken') || '';
  }
  async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    const t = token();
    if (t) headers['X-Admin-Token'] = t;
    const res = await fetch(path, { credentials: 'include', ...opts, headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.message || 'Хато');
    return data;
  }
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  async function load() {
    const body = $('lbGlobalBody');
    if (!body) return;
    try {
      const data = await api('/api/admin/leaderboard?limit=100');
      const s = data.settings || {};
      if ($('lbPublicToggle')) $('lbPublicToggle').checked = s.public !== false;
      if ($('lbTitleInput')) $('lbTitleInput').value = s.title || '';
      if ($('lbShowSchool')) $('lbShowSchool').checked = s.showSchool !== false;
      if ($('lbShowClass')) $('lbShowClass').checked = s.showClass !== false;
      if ($('lbUseDemo')) $('lbUseDemo').checked = s.useDemo !== false;
      paintPins(s.pinned || []);
      const entries = data.entries || [];
      body.innerHTML = entries.map((e) => {
        const uid = esc(e.id || e.userId || '');
        const nm = esc(e.name || '');
        const isDemo = e.kind === 'demo';
        return `<tr>
        <td>${e.rank}</td>
        <td>${nm}${isDemo ? ' <span class="muted">(demo)</span>' : ''}</td>
        <td>${esc(e.school || '')}</td>
        <td>${esc(e.className || '')}</td>
        <td><b>${esc(e.rating)}</b></td>
        <td>${esc(e.solved || 0)}</td>
        <td>${esc(e.contests || 0)}</td>
        <td style="white-space:nowrap">
          ${isDemo ? '—' : `
          <button type="button" class="btn small" data-pin-rank="1" data-pin-id="${uid}" data-pin-name="${nm}">1</button>
          <button type="button" class="btn small" data-pin-rank="2" data-pin-id="${uid}" data-pin-name="${nm}">2</button>
          <button type="button" class="btn small" data-pin-rank="3" data-pin-id="${uid}" data-pin-name="${nm}">3</button>
          <button type="button" class="btn small" data-pin-rank="ask" data-pin-id="${uid}" data-pin-name="${nm}">N…</button>
          `}
        </td>
      </tr>`;
      }).join('') || '<tr><td colspan="8">Холӣ</td></tr>';

      body.querySelectorAll('[data-pin-rank]').forEach((btn) => {
        btn.addEventListener('click', () => pinFromRow(btn));
      });

      if ($('lbMsg')) {
        let msg = (data.total || entries.length) + ' нафар';
        if (data.demo) msg += ' · demo (натиҷаҳо ҳанӯз нестанд)';
        if (data.message) msg += ' · ' + data.message;
        $('lbMsg').textContent = msg;
      }
    } catch (e) {
      if ($('lbMsg')) $('lbMsg').textContent = e.message;
      if (body) body.innerHTML = `<tr><td colspan="8">${esc(e.message)}</td></tr>`;
    }
  }

  async function pinFromRow(btn) {
    const userId = (btn.dataset.pinId || '').trim();
    const name = (btn.dataset.pinName || '').trim();
    let rank = btn.dataset.pinRank;
    if (rank === 'ask') {
      const v = prompt('Ҷойро ворид кунед (1, 2, 3…):', '1');
      if (v == null) return;
      rank = Number(v);
    } else {
      rank = Number(rank);
    }
    if (!userId || !rank || rank < 1) {
      if ($('lbMsg')) $('lbMsg').textContent = 'userId ва rank лозим';
      return;
    }
    try {
      const s = await api('/api/admin/leaderboard/settings');
      const pinned = (s.pinned || []).filter((p) => String(p.userId || p.id) !== userId);
      pinned.push({ userId, rank, name });
      pinned.sort((a, b) => a.rank - b.rank);
      await api('/api/admin/leaderboard/settings', {
        method: 'POST',
        body: JSON.stringify({ pinned }),
      });
      if ($('lbMsg')) $('lbMsg').textContent = `Pin #${rank} · ${name || userId} ✓`;
      await load();
    } catch (e) {
      if ($('lbMsg')) $('lbMsg').textContent = e.message;
    }
  }

  function paintPins(pins) {
    const box = $('pinList');
    if (!box) return;
    if (!pins.length) {
      box.textContent = 'Pinned нест';
      return;
    }
    box.innerHTML = pins
      .map(
        (p, i) =>
          `<div style="margin:.25rem 0">#${p.rank} · ${esc(p.userId || p.id)} · ${esc(p.name || '')}
        <button type="button" data-pin-del="${i}" class="btn small" style="margin-left:.35rem">×</button></div>`
      )
      .join('');
    box.querySelectorAll('[data-pin-del]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const idx = Number(btn.dataset.pinDel);
        try {
          const s = await api('/api/admin/leaderboard/settings');
          const pinned = (s.pinned || []).filter((_, i) => i !== idx);
          await api('/api/admin/leaderboard/settings', {
            method: 'POST',
            body: JSON.stringify({ pinned }),
          });
          if ($('lbMsg')) $('lbMsg').textContent = 'Pin нест карда шуд';
          await load();
        } catch (e) {
          if ($('lbMsg')) $('lbMsg').textContent = e.message;
        }
      });
    });
  }

  async function saveSettings() {
    try {
      const payload = {
        public: $('lbPublicToggle') ? $('lbPublicToggle').checked : true,
        title: $('lbTitleInput') ? $('lbTitleInput').value : '',
        showSchool: $('lbShowSchool') ? $('lbShowSchool').checked : true,
        showClass: $('lbShowClass') ? $('lbShowClass').checked : true,
        useDemo: $('lbUseDemo') ? $('lbUseDemo').checked : true,
      };
      await api('/api/admin/leaderboard/settings', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if ($('lbMsg')) $('lbMsg').textContent = 'Сабт шуд ✓';
      await load();
    } catch (e) {
      if ($('lbMsg')) $('lbMsg').textContent = e.message;
    }
  }

  async function addPin() {
    const userId = ($('pinUserId') && $('pinUserId').value.trim()) || '';
    const rank = Number(($('pinRank') && $('pinRank').value) || 0);
    const name = ($('pinName') && $('pinName').value.trim()) || '';
    if (!userId || !rank) {
      if ($('lbMsg')) $('lbMsg').textContent = 'userId ва rank лозим';
      return;
    }
    try {
      const s = await api('/api/admin/leaderboard/settings');
      const pinned = (s.pinned || []).filter((p) => String(p.userId || p.id) !== userId);
      pinned.push({ userId, rank, name });
      pinned.sort((a, b) => a.rank - b.rank);
      await api('/api/admin/leaderboard/settings', {
        method: 'POST',
        body: JSON.stringify({ pinned }),
      });
      if ($('pinUserId')) $('pinUserId').value = '';
      if ($('pinRank')) $('pinRank').value = '';
      if ($('pinName')) $('pinName').value = '';
      if ($('lbMsg')) $('lbMsg').textContent = `Pin #${rank} ✓`;
      await load();
    } catch (e) {
      if ($('lbMsg')) $('lbMsg').textContent = e.message;
    }
  }

  function bind() {
    const save = $('lbSaveSettings');
    const ref = $('lbRefresh');
    const pin = $('pinAdd');
    if (save) save.addEventListener('click', saveSettings);
    if (ref) ref.addEventListener('click', load);
    if (pin) pin.addEventListener('click', addPin);
    document.querySelectorAll('.tab[data-tab="leaderboard"]').forEach((t) => {
      t.addEventListener('click', () => setTimeout(load, 80));
    });
    const panel = $('tab-leaderboard');
    if (panel && !panel.classList.contains('hidden')) {
      setTimeout(load, 50);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
