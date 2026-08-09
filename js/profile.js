(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  function token() {
    return localStorage.getItem('geo_user_token') || localStorage.getItem('userToken') || '';
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    const t = token();
    if (t) headers['Authorization'] = 'Bearer ' + t;
    if (t) headers['X-User-Token'] = t;
    const res = await fetch(path, Object.assign({}, opts, { headers }));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'Хато');
    return data;
  }

  function paintProfile(profile, stats) {
    $('#loginGate')?.classList.add('hidden');
    $('#profileApp')?.classList.remove('hidden');

    const name = profile.name || 'Иштирокчӣ';
    $('#prName').textContent = name;
    $('#prEmail').textContent = profile.email || '';
    const genderLabel = profile.gender === 'male' ? 'Писар' : profile.gender === 'female' ? 'Духтар' : '—';
    const bits = [genderLabel, profile.className, profile.school, profile.region].filter(Boolean);
    $('#prMeta').textContent = bits.join(' · ') || 'Профил нопурра';
    $('#prGender').textContent = genderLabel;
    $('#prSchool').textContent = profile.school || '—';
    $('#prRegion').textContent = profile.region || '—';
    $('#prClass').textContent = profile.className || '—';
    $('#prRating').textContent = String(profile.rating || 1200);
    $('#prMaxRating').textContent = String(profile.maxRating || profile.rating || 1200);

    const av = $('#prAvatar');
    const pic = profile.picture || profile.avatarUrl;
    if (pic) av.innerHTML = `<img src="${pic}" alt="" />`;
    else av.textContent = name.trim().slice(0, 1).toUpperCase();

    const topAv = $('#pfAvatar');
    if (topAv) {
      if (pic) topAv.innerHTML = `<img src="${pic}" alt="" />`;
      else topAv.textContent = name.trim().slice(0, 1).toUpperCase();
    }

    const st = stats || {};
    $('#prContests').textContent = String(st.attempts || 0);
    $('#prSolved').textContent = String(st.passed || st.problemsSolved || 0);
    $('#prFailed').textContent = String(st.failed || 0);

    const pct = Math.min(100, 20 + (st.passed || 0) * 12);
    const bar = $('#prBar');
    if (bar) bar.style.width = pct + '%';
    $('#prProgressText').textContent = profile.profileComplete
      ? `${st.passed || 0} викторина гузашт`
      : 'Профилро пурра кунед';

    const recent = st.recent || [];
    const box = $('#prRecent');
    if (box) {
      box.innerHTML = recent.length
        ? recent
            .map(
              (r) => `<div class="pr-row"><span>${esc(r.title)}</span><span>${r.score ?? '—'}% · ${esc(r.status || '')}</span></div>`
            )
            .join('')
        : '<p class="pr-muted">Ҳоло супориш нест</p>';
    }

    // settings form
    if ($('#fName')) $('#fName').value = profile.name || '';
    if ($('#fGender')) $('#fGender').value = profile.gender || '';
    if ($('#fSchool')) $('#fSchool').value = profile.school || '';
    if ($('#fRegion')) $('#fRegion').value = profile.region || '';
    if ($('#fClass')) $('#fClass').value = profile.className || '';

    if (!profile.profileComplete) {
      $('#onboardModal')?.classList.remove('hidden');
    }
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  async function load() {
    if (!token()) {
      $('#loginGate')?.classList.remove('hidden');
      $('#profileApp')?.classList.add('hidden');
      initGoogle();
      return;
    }
    try {
      const data = await api('/api/me/profile');
      paintProfile(data.profile || {}, data.stats || {});
      if (data.needsOnboarding) $('#onboardModal')?.classList.remove('hidden');
    } catch (e) {
      console.warn(e);
      localStorage.removeItem('geo_user_token');
      localStorage.removeItem('userToken');
      $('#loginGate')?.classList.remove('hidden');
      initGoogle();
    }
  }

  async function initGoogle() {
    const host = $('#googleSignInBtn');
    if (!host) return;
    try {
      const res = await fetch('/api/auth/google/status');
      const status = await res.json();
      if (!status.configured || !status.clientId) {
        host.innerHTML = '<p class="pr-muted">Google Auth танзим нашудааст</p>';
        return;
      }
      function start() {
        if (!window.google || !google.accounts || !google.accounts.id) return false;
        google.accounts.id.initialize({
          client_id: status.clientId,
          callback: async (r) => {
            try {
              const res2 = await fetch('/api/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idToken: r.credential }),
              });
              const data = await res2.json();
              if (!res2.ok) throw new Error(data.error || 'Login failed');
              if (data.token) {
                localStorage.setItem('geo_user_token', data.token);
                localStorage.setItem('userToken', data.token);
              }
              localStorage.setItem('geo_user', JSON.stringify(data.user || {}));
              localStorage.setItem('currentUser', JSON.stringify(data.user || {}));
              location.reload();
            } catch (err) {
              alert(err.message);
            }
          },
          auto_select: false,
          ux_mode: 'popup',
        });
        google.accounts.id.renderButton(host, {
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text: 'continue_with',
          width: 280,
        });
        return true;
      }
      if (!start()) {
        let n = 0;
        const t = setInterval(() => {
          n++;
          if (start() || n > 40) clearInterval(t);
        }, 200);
      }
    } catch (_) {}
  }

  $$('.pr-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.pr-tab').forEach((b) => b.classList.remove('active'));
      $$('.pr-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      $('#tab-' + btn.dataset.tab)?.classList.add('active');
    });
  });

  $('#prForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const data = await api('/api/me/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          name: $('#fName').value.trim(),
          gender: $('#fGender').value,
          school: $('#fSchool').value.trim(),
          region: $('#fRegion').value.trim(),
          className: $('#fClass').value.trim(),
        }),
      });
      $('#prFormMsg').textContent = 'Сабт шуд';
      paintProfile(data.profile, (await api('/api/me/profile')).stats);
    } catch (err) {
      $('#prFormMsg').textContent = err.message;
    }
  });

  $('#onboardForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/me/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          gender: $('#oGender').value,
          school: $('#oSchool').value.trim(),
          region: $('#oRegion').value.trim(),
          className: $('#oClass').value.trim(),
        }),
      });
      $('#onboardModal')?.classList.add('hidden');
      load();
    } catch (err) {
      $('#oMsg').textContent = err.message;
    }
  });

  $('#prLogout')?.addEventListener('click', () => {
    localStorage.removeItem('geo_user_token');
    localStorage.removeItem('userToken');
    localStorage.removeItem('geo_user');
    localStorage.removeItem('currentUser');
    location.href = '/';
  });

  load();
})();
