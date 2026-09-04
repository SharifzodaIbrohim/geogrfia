(() => {
  const $ = (s, r = document) => r.querySelector(s);

  function setTheme(mode) {
    document.body.classList.toggle('light-theme', mode === 'light');
    localStorage.setItem('geo_theme', mode);
  }
  if (localStorage.getItem('geo_theme') === 'light') setTheme('light');

  $('#pfTheme')?.addEventListener('click', () => {
    setTheme(document.body.classList.contains('light-theme') ? 'dark' : 'light');
  });

  const drawer = $('#pfNotifDrawer');
  $('#pfNotif')?.addEventListener('click', (e) => {
    e.stopPropagation();
    drawer?.classList.toggle('hidden');
  });
  document.addEventListener('click', () => drawer?.classList.add('hidden'));

  $('#pfAvatar')?.addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('authToggle')?.click();
  });

  document.querySelectorAll('.pf-nav a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href');
      if (!id || id === '#') return;
      const el = document.querySelector(id);
      if (el) {
        e.preventDefault();
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  async function loadHomeData() {
    try {
      const [quizzes, oly] = await Promise.all([
        fetch('/api/quizzes').then((r) => r.json()).catch(() => ({ quizzes: [] })),
        fetch('/api/olympiads/active').then((r) => r.json()).catch(() => ({ olympiads: [] })),
      ]);
      const qBox = $('#pfFeaturedQuizzes');
      if (qBox) {
        const list = (quizzes.quizzes || []).slice(0, 4);
        qBox.innerHTML = list.length
          ? list
              .map(
                (q) => `<a class="pf-card" href="/quiz" style="text-decoration:none;color:inherit">
            <h3>${esc(q.title)}</h3>
            <p>${esc(q.description || (q.questionCount || 0) + ' савол')}</p>
            <span class="pf-tag">Викторина · ҳад ${q.passScore || 70}%</span>
          </a>`
              )
              .join('')
          : `<div class="pf-card"><h3>Викторинаҳо</h3><p>Аз /quiz кушоед.</p></div>`;
      }
      const oBox = $('#pfUpcomingOly');
      if (oBox) {
        const list = (oly.olympiads || []).slice(0, 4);
        oBox.innerHTML = list.length
          ? list
              .map(
                (o) => `<a class="pf-card" href="/student" style="text-decoration:none;color:inherit">
            <h3>${esc(o.title)}</h3>
            <p>${o.questionCount || 0} савол · ҳад ${o.passScore || 70}%</p>
            <span class="pf-tag">${o.type === 'quiz' ? 'Викторина' : 'Олимпиада'}</span>
          </a>`
              )
              .join('')
          : `<div class="pf-card"><h3>Олимпиадаҳо</h3><p>Воридшавӣ: /student</p></div>`;
      }
      const st = $('#pfStatQuizzes');
      if (st) st.textContent = String((quizzes.quizzes || []).length);
      const so = $('#pfStatOlympiads');
      if (so) so.textContent = String((oly.olympiads || []).length);
    } catch (e) {
      console.warn(e);
    }
  }

  try {
    const u = JSON.parse(
      localStorage.getItem('geo_user') || localStorage.getItem('currentUser') || 'null'
    );
    const av = $('#pfAvatar');
    if (u && av) {
      if (u.picture) av.innerHTML = `<img src="${u.picture}" alt="" />`;
      else if (u.name) av.textContent = u.name.trim().slice(0, 1).toUpperCase();
    }
  } catch (_) {}

  function ensureMobileSettingsSheet() {
    if (document.getElementById('mobileSettingsSheet')) return;
    const sheet = document.createElement('div');
    sheet.id = 'mobileSettingsSheet';
    sheet.innerHTML = `
      <div class="mss-card" role="dialog" aria-label="Settings">
        <div class="mss-head">
          <h3 data-i18n="navSettings">Танзимот</h3>
          <button type="button" class="mss-close" id="mssClose" aria-label="Close">×</button>
        </div>
        <div class="mss-row">
          <div>
            <span class="mss-label" data-i18n="language">Забон</span>
            <span class="mss-hint">TJ / RU / EN</span>
          </div>
          <select id="mssLang">
            <option value="tg">TJ — Тоҷикӣ</option>
            <option value="ru">RU — Русский</option>
            <option value="en">EN — English</option>
          </select>
        </div>
        <div class="mss-row">
          <div>
            <span class="mss-label" data-i18n="theme">Тема</span>
            <span class="mss-hint">Dark / Light</span>
          </div>
          <button type="button" class="mss-theme-btn" id="mssTheme">🌙 Dark</button>
        </div>
      </div>`;
    document.body.appendChild(sheet);

    const close = () => sheet.classList.remove('open');
    sheet.querySelector('#mssClose')?.addEventListener('click', close);
    sheet.addEventListener('click', (e) => { if (e.target === sheet) close(); });

    const langSel = sheet.querySelector('#mssLang');
    const cur = (localStorage.getItem('geografia_lang') || localStorage.getItem('geo_lang') || localStorage.getItem('siteLanguage') || 'tg').toLowerCase();
    if (langSel) {
      langSel.value = cur === 'tj' ? 'tg' : (['tg','ru','en'].includes(cur) ? cur : 'tg');
      langSel.addEventListener('change', () => {
        const code = langSel.value;
        localStorage.setItem('geografia_lang', code);
        localStorage.setItem('geo_lang', code);
        localStorage.setItem('siteLanguage', code);
        const pf = document.getElementById('pfLang');
        if (pf) pf.value = code === 'tg' ? 'tg' : code;
        try {
          if (window.GeoI18n && window.GeoI18n.setLang) window.GeoI18n.setLang(code);
          else if (window.GeoI18n && window.GeoI18n.apply) window.GeoI18n.apply();
        } catch (_) {}
        window.dispatchEvent(new CustomEvent('geo:lang', { detail: code }));
      });
    }

    const themeBtn = sheet.querySelector('#mssTheme');
    const syncThemeBtn = () => {
      if (!themeBtn) return;
      const light = document.body.classList.contains('light-theme');
      themeBtn.textContent = light ? '☀️ Light' : '🌙 Dark';
    };
    syncThemeBtn();
    themeBtn?.addEventListener('click', () => {
      const next = document.body.classList.contains('light-theme') ? 'dark' : 'light';
      setTheme(next);
      syncThemeBtn();
    });
  }

  function openMobileSettings() {
    ensureMobileSettingsSheet();
    const sheet = document.getElementById('mobileSettingsSheet');
    if (sheet) sheet.classList.add('open');
    try { if (window.GeoI18n && window.GeoI18n.apply) window.GeoI18n.apply(); } catch (_) {}
  }

  function markBottomNavActive() {
    const path = (location.pathname || '/').replace(/\/+$/, '') || '/';
    const map = {
      '/': 'countries',
      '/countries': 'countries',
      '/courses': 'courses',
      '/student': 'olympiads',
      '/profile': 'profile',
      '/quiz': 'courses',
      '/leaderboard': 'olympiads',
    };
    const key = map[path] || '';
    document.querySelectorAll('#mobileBottomNav .nav-item').forEach((el) => {
      el.classList.toggle('active', el.getAttribute('data-nav') === key);
    });
  }

  document.getElementById('bottomSettingsBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    openMobileSettings();
  });
  document.addEventListener('click', (e) => {
    const btn = e.target.closest && e.target.closest('#bottomSettingsBtn');
    if (btn) {
      e.preventDefault();
      openMobileSettings();
    }
  });
  markBottomNavActive();
  try { if (window.GeoI18n && window.GeoI18n.apply) window.GeoI18n.apply(); } catch (_) {}

  loadHomeData();
})();
