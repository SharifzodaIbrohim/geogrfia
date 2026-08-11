(() => {
  const $ = (id) => document.getElementById(id);

  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    const token = localStorage.getItem('geo_admin_token') || '';
    if (token) headers['X-Admin-Token'] = token;
    const res = await fetch(path, { ...options, headers, credentials: 'include' });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function paintPins(pinned) {
    const box = $('pinList');
    if (!box) return;
    if (!pinned || !pinned.length) {
      box.textContent = '—';
      return;
    }
    box.innerHTML = pinned
      .map(
        (p, i) =>
          `<div style="display:flex;gap:.5rem;align-items:center;margin:.25rem 0">` +
          `<span>#${p.rank} ${p.name || p.userId || ''}</span>` +
          `<button type="button" class="btn" data-pin-del="${i}">×</button></div>`
      )
      .join('');
    box.querySelectorAll('[data-pin-del]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const idx = Number(btn.dataset.pinDel);
        const s = await api('/api/admin/leaderboard/settings');
        const pinned2 = (s.pinned || s.settings?.pinned || []).filter((_, i) => i !== idx);
        await api('/api/admin/leaderboard/settings', {
          method: 'POST',
          body: JSON.stringify({ pinned: pinned2 }),
        });
        load();
      });
    });
  }

  async function load() {
    try {
      const s = await api('/api/admin/leaderboard/settings');
      const conf = s.settings || s;
      if ($('lbPublicToggle')) $('lbPublicToggle').checked = conf.public !== false;
      if ($('lbTitleInput')) $('lbTitleInput').value = conf.title || '';
      if ($('lbHideNames')) $('lbHideNames').checked = !!conf.hideNames;
      if ($('lbShowSchool')) $('lbShowSchool').checked = conf.showSchool !== false;
      if ($('lbShowClass')) $('lbShowClass').checked = conf.showClass !== false;
      if ($('lbShowScore')) $('lbShowScore').checked = conf.showScore !== false;
      if ($('lbUseDemo')) $('lbUseDemo').checked = conf.useDemo !== false;
      paintPins(conf.pinned || []);

      const data = await api('/api/admin/leaderboard?limit=100');
      const body = $('lbGlobalBody');
      if (body) {
        const rows = data.entries || [];
        body.innerHTML = rows
          .map(
            (e) => `<tr>
            <td>${e.rank ?? ''}</td>
            <td>${esc(e.name)}</td>
            <td>${esc(e.school || '')}</td>
            <td>${esc(e.className || '')}</td>
            <td>${e.rating ?? e.score ?? '—'}</td>
            <td>${e.solved ?? '—'}</td>
            <td>${e.contests ?? '—'}</td>
          </tr>`
          )
          .join('') || '<tr><td colspan="7">Холӣ</td></tr>';
      }
    } catch (e) {
      if ($('lbMsg')) $('lbMsg').textContent = e.message;
    }
  }

  async function saveSettings() {
    try {
      const payload = {
        public: $('lbPublicToggle') ? $('lbPublicToggle').checked : true,
        title: $('lbTitleInput') ? $('lbTitleInput').value : '',
        hideNames: $('lbHideNames') ? $('lbHideNames').checked : false,
        showSchool: $('lbShowSchool') ? $('lbShowSchool').checked : true,
        showClass: $('lbShowClass') ? $('lbShowClass').checked : true,
        showScore: $('lbShowScore') ? $('lbShowScore').checked : true,
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
      alert('userId ва rank лозим');
      return;
    }
    const s = await api('/api/admin/leaderboard/settings');
    const conf = s.settings || s;
    const pinned = (conf.pinned || []).filter((p) => String(p.userId || p.id) !== userId);
    pinned.push({ userId, rank, name });
    pinned.sort((a, b) => a.rank - b.rank);
    await api('/api/admin/leaderboard/settings', {
      method: 'POST',
      body: JSON.stringify({ pinned }),
    });
    if ($('pinUserId')) $('pinUserId').value = '';
    if ($('pinRank')) $('pinRank').value = '';
    if ($('pinName')) $('pinName').value = '';
    load();
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function bind() {
    $('lbSaveSettings')?.addEventListener('click', saveSettings);
    $('lbRefresh')?.addEventListener('click', load);
    $('pinAdd')?.addEventListener('click', addPin);
    document.querySelectorAll('.tab[data-tab="leaderboard"]').forEach((t) => {
      t.addEventListener('click', () => setTimeout(load, 50));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      bind();
      load();
    });
  } else {
    bind();
    load();
  }
})();
