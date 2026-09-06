(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  function token() {
    return localStorage.getItem('geo_user_token') || localStorage.getItem('userToken') || '';
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    const t = token();
    if (t) {
      headers['Authorization'] = 'Bearer ' + t;
      headers['X-User-Token'] = t;
    }
    const res = await fetch(path, Object.assign({}, opts, { headers }));
    const raw = await res.text();
    let data = {};
    try { data = raw ? JSON.parse(raw) : {}; } catch (_) {
      data = { error: 'Ҷавоби ғайри-JSON', detail: raw.slice(0, 180) };
    }
    if (!res.ok) {
      const parts = [];
      if (data.error) parts.push(String(data.error));
      if (data.detail) parts.push(String(data.detail));
      if (data.reason) parts.push(String(data.reason));
      if (!parts.length) parts.push('Хато HTTP ' + res.status);
      else parts.push('(HTTP ' + res.status + ')');
      throw new Error(parts.join(' — '));
    }
    return data;
  }

  function tierLabel(rating) {
    const r = Number(rating) || 1200;
    if (r >= 2200) return 'Legend';
    if (r >= 2000) return 'Master';
    if (r >= 1800) return 'Gold';
    if (r >= 1600) return 'Silver';
    if (r >= 1400) return 'Bronze';
    if (r >= 1200) return 'Newbie+';
    return 'Newbie';
  }

  function progressToNext(rating) {
    const r = Number(rating) || 1200;
    const tiers = [1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500];
    let next = tiers.find((t) => t > r) || r + 200;
    const prev = [...tiers].reverse().find((t) => t <= r) || 1000;
    const pct = Math.min(100, Math.max(6, ((r - prev) / Math.max(1, next - prev)) * 100));
    const need = Math.max(0, next - r);
    return { pct, need, next, nextLabel: tierLabel(next), currentLabel: tierLabel(r) };
  }

  function escapeHtml(s) {
    const amp = String.fromCharCode(38);
    return String(s || '')
      .replace(/&/g, amp + 'amp;')
      .replace(/</g, amp + 'lt;')
      .replace(/>/g, amp + 'gt;')
      .replace(/"/g, amp + 'quot;');
  }

  function formatWhen(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString('tg-TJ', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch (_) {
      return String(iso).slice(0, 16);
    }
  }

  function rowHtml(r) {
    const ok =
      (r.status || '').toLowerCase() === 'passed' ||
      (r.score != null && Number(r.score) >= 70);
    const badge = ok
      ? '<span class="pr-badge ok">Гузашт</span>'
      : '<span class="pr-badge fail">Нагузашт</span>';
    const score =
      r.score != null
        ? '<span style="font-weight:700;color:#70db97">' + Number(r.score).toFixed(0) + '%</span>'
        : '';
    const delta =
      r.ratingDelta != null && Number(r.ratingDelta) !== 0
        ? '<span class="pr-delta ' + (Number(r.ratingDelta) > 0 ? 'up' : 'down') + '">' +
          (Number(r.ratingDelta) > 0 ? '+' : '') + Number(r.ratingDelta) + '</span>'
        : '';
    return (
      '<div class="pr-row"><div><b>' +
      escapeHtml(r.title || 'Супориш') +
      '</b><div class="pr-muted" style="font-size:0.78rem;margin-top:.15rem">' +
      escapeHtml(formatWhen(r.finishedAt)) +
      '</div></div><div style="display:flex;gap:0.55rem;align-items:center;flex-shrink:0">' +
      score + delta + badge +
      '</div></div>'
    );
  }

  function paintProfile(profile, stats) {
    $('#loginGate')?.classList.add('hidden');
    $('#profileApp')?.classList.remove('hidden');

    const name = profile.name || 'Иштирокчӣ';
    const setText = (sel, val) => {
      const el = $(sel);
      if (el) el.textContent = val == null ? '' : String(val);
    };
    const setHtml = (sel, html) => {
      const el = $(sel);
      if (el) el.innerHTML = html;
    };

    setText('#prName', name);
    setText('#prEmail', profile.email || '');

    const genderLabel =
      profile.gender === 'male' ? 'Писар' : profile.gender === 'female' ? 'Духтар' : '—';
    const locBits = [];
    if (profile.region) locBits.push('TJ · ' + profile.region);
    else locBits.push('TJ');
    if (profile.className) locBits.push('синф ' + profile.className);
    if (profile.school) locBits.push(profile.school);
    setText('#prMeta', locBits.join(' · '));

    setText('#prGender', genderLabel);
    setText('#prSchool', profile.school || '—');
    setText('#prRegion', profile.region || '—');
    setText('#prClass', profile.className || '—');

    const rating = Number(profile.rating) || 1200;
    const maxR = Math.max(Number(profile.maxRating) || rating, rating);
    setText('#prRating', String(rating));
    setText('#prMaxRating', String(maxR));

    const deltaEl = $('#prDelta');
    if (deltaEl) {
      const d = rating - 1200;
      if (d > 0) {
        deltaEl.textContent = '+' + d;
        deltaEl.className = 'pr-delta up';
      } else if (d < 0) {
        deltaEl.textContent = String(d);
        deltaEl.className = 'pr-delta down';
      } else {
        deltaEl.textContent = '';
        deltaEl.className = 'pr-delta flat';
      }
    }

    const pic = profile.picture || profile.avatarUrl || profile.avatar;
    const av = $('#prAvatar');
    if (av) {
      if (pic) av.innerHTML = '<img src="' + String(pic).replace(/"/g, '') + '" alt="" />';
      else av.textContent = name.trim().slice(0, 1).toUpperCase() || '?';
    }
    const topAv = $('#pfAvatar');
    if (topAv) {
      if (pic) topAv.innerHTML = '<img src="' + String(pic).replace(/"/g, '') + '" alt="" />';
      else topAv.textContent = name.trim().slice(0, 1).toUpperCase() || 'G';
    }

    const st = stats || {};
    const attempts = Number(st.attempts || st.contests || 0);
    const passed = Number(st.passed || st.problemsSolved || 0);
    const failed = Number(st.failed || Math.max(0, attempts - passed));

    setText('#prContests', String(attempts));
    setText('#prSolved', String(passed));
    setText('#prPassed', String(passed));
    setText('#prFailed', String(failed));
    setText('#prAttempts', String(attempts));

    const prog = progressToNext(rating);
    const bar = $('#prBar');
    if (bar) bar.style.width = prog.pct + '%';

    let progressText = '';
    if (!profile.profileComplete) {
      progressText = 'Профилро пурра кунед ва викторина супоред';
    } else if (prog.need > 0) {
      progressText = rating + ' → ' + prog.next + ' · ' + prog.need + ' балл то ' + prog.nextLabel;
    } else {
      progressText = 'Сатҳи баландтарин';
    }
    setText('#prProgressText', progressText);
    setText('#prTier', prog.currentLabel + ' · Rating ' + rating);

    if ($('#fName')) $('#fName').value = profile.name || '';
    if ($('#fGender')) $('#fGender').value = profile.gender || '';
    if ($('#fSchool')) $('#fSchool').value = profile.school || '';
    if ($('#fRegion')) $('#fRegion').value = profile.region || '';
    if ($('#fClass')) $('#fClass').value = profile.className || '';

    const recent = st.recent || [];
    const empty = '<p class="pr-muted">Ҳоло холӣ — викторина супоред то натиҷа пайдо шавад.</p>';
    const listHtml = recent.length === 0 ? empty : recent.map(rowHtml).join('');

    setHtml('#prRecent', listHtml);
    setHtml('#prActivity', listHtml);

    const histEl = $('#prHistory');
    if (histEl) {
      histEl.innerHTML = !recent.length
        ? '<p class="pr-muted">Баъди супоридани викторинаҳо таърихи рейтинг пайдо мешавад.</p>'
        : recent.map(rowHtml).join('');
    }

    const contestsEl = $('#prContestsList');
    if (contestsEl) {
      contestsEl.innerHTML = !recent.length
        ? '<p class="pr-muted">Ҳоло мусобиқа нест. Аз <a href="/quiz" style="color:#70db97">Викторинаҳо</a> оғоз кунед.</p>'
        : recent.map(rowHtml).join('');
    }
  }

  function showOnboarding(needs) {
    const modal = $('#onboardModal');
    if (!modal) return;
    if (needs) modal.classList.remove('hidden');
    else modal.classList.add('hidden');
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
      try {
        paintProfile(data.profile || {}, data.stats || {});
        showOnboarding(!!data.needsOnboarding);
      } catch (paintErr) {
        console.warn('paintProfile', paintErr);
        $('#loginGate')?.classList.add('hidden');
        $('#profileApp')?.classList.remove('hidden');
      }
    } catch (err) {
      console.warn('profile load', err);
      const msg = (err && err.message) || 'Хатои профил';
      const isAuth = /401|ворид|Дастрасӣ|Unauthorized|token/i.test(msg);
      if (isAuth) {
        localStorage.removeItem('geo_user_token');
        localStorage.removeItem('userToken');
        localStorage.removeItem('geo_user');
        localStorage.removeItem('currentUser');
        $('#loginGate')?.classList.remove('hidden');
        $('#profileApp')?.classList.add('hidden');
        initGoogle();
        const host = document.getElementById('googleSignInBtn');
        if (host && host.parentNode) {
          let e = host.parentNode.querySelector('.pr-login-err');
          if (!e) {
            e = document.createElement('p');
            e.className = 'pr-muted pr-login-err';
            e.style.color = '#f88';
            e.style.marginTop = '0.5rem';
            host.parentNode.insertBefore(e, host.nextSibling);
          }
          e.textContent = msg;
        }
      } else {
        alert('Профил: ' + msg);
        $('#loginGate')?.classList.add('hidden');
        $('#profileApp')?.classList.remove('hidden');
      }
    }
  }

  function initGoogle() {
    try {
      const host = $('#googleSignInBtn');
      if (!host) return;
      const start = () => {
        if (!window.google || !google.accounts || !google.accounts.id) return false;
        const meta = document.querySelector('meta[name="google-client-id"]');
        const clientId =
          (meta && meta.content) ||
          window.GOOGLE_CLIENT_ID ||
          localStorage.getItem('geo_google_client_id') ||
          '';
        if (!clientId) {
          fetch('/api/auth/google/status')
            .then((r) => r.json())
            .then((d) => {
              const id = d.clientId || d.client_id;
              if (id) {
                window.GOOGLE_CLIENT_ID = id;
                localStorage.setItem('geo_google_client_id', id);
                initGoogle();
              }
            })
            .catch(() => {});
          host.innerHTML =
            '<p class="pr-muted">Google Sign-In бор мешавад…</p>';
          return true;
        }
        google.accounts.id.initialize({
          client_id: clientId,
          callback: async (resp) => {
            try {
              if (!resp || !resp.credential) {
                throw new Error('Google credential нест — бори дигар кӯшиш кунед');
              }
              const data = await api('/api/auth/google', {
                method: 'POST',
                body: JSON.stringify({
                  idToken: resp.credential,
                  credential: resp.credential,
                }),
              });
              if (!data.token) {
                throw new Error(data.error || 'Token аз сервер наомад');
              }
              if (String(data.token).split('.').length !== 3) {
                throw new Error('Token JWT нест (формати нодуруст)');
              }
              localStorage.setItem('geo_user_token', data.token);
              localStorage.setItem('userToken', data.token);
              localStorage.setItem('geo_user', JSON.stringify(data.user || {}));
              localStorage.setItem('currentUser', JSON.stringify(data.user || {}));
              location.reload();
            } catch (err) {
              console.error('Google login', err);
              const msg = (err && err.message) || 'Хатои Google login';
              alert(msg);
              const hostEl = document.getElementById('googleSignInBtn');
              if (hostEl) {
                let e = hostEl.parentNode && hostEl.parentNode.querySelector('.pr-login-err');
                if (!e) {
                  e = document.createElement('p');
                  e.className = 'pr-muted pr-login-err';
                  e.style.color = '#f88';
                  e.style.marginTop = '0.5rem';
                  if (hostEl.parentNode) hostEl.parentNode.insertBefore(e, hostEl.nextSibling);
                }
                e.textContent = msg;
              }
            }
          },
          auto_select: false,
        });
        host.innerHTML = '';
        google.accounts.id.renderButton(host, {
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text: 'continue_with',
          width: 280,
        });
        return true;
      };
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
          name: ($('#fName') && $('#fName').value.trim()) || '',
          gender: ($('#fGender') && $('#fGender').value) || '',
          school: ($('#fSchool') && $('#fSchool').value.trim()) || '',
          region: ($('#fRegion') && $('#fRegion').value.trim()) || '',
          className: ($('#fClass') && $('#fClass').value.trim()) || '',
        }),
      });
      if ($('#prFormMsg')) $('#prFormMsg').textContent = 'Сабт шуд \u2713';
      const again = await api('/api/me/profile');
      paintProfile(again.profile || data.profile, again.stats || {});
      showOnboarding(!!again.needsOnboarding);
    } catch (err) {
      if ($('#prFormMsg')) $('#prFormMsg').textContent = err.message;
    }
  });

  $('#onboardForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/me/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          gender: ($('#oGender') && $('#oGender').value) || '',
          school: ($('#oSchool') && $('#oSchool').value.trim()) || '',
          region: ($('#oRegion') && $('#oRegion').value.trim()) || '',
          className: ($('#oClass') && $('#oClass').value.trim()) || '',
        }),
      });
      $('#onboardModal')?.classList.add('hidden');
      load();
    } catch (err) {
      const m = $('#oMsg');
      if (m) m.textContent = err.message;
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
