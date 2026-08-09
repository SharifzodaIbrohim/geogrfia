(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  function setTheme(mode) {
    document.body.classList.toggle('light-theme', mode === 'light');
    localStorage.setItem('geo_theme', mode);
  }
  const saved = localStorage.getItem('geo_theme');
  if (saved === 'light') setTheme('light');

  const themeBtn = $('#pfTheme');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const next = document.body.classList.contains('light-theme') ? 'dark' : 'light';
      setTheme(next);
    });
  }

  const notifBtn = $('#pfNotif');
  const drawer = $('#pfNotifDrawer');
  if (notifBtn && drawer) {
    notifBtn.addEventListener('click', () => {
      drawer.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
      if (!drawer.classList.contains('hidden') && !drawer.contains(e.target) && e.target !== notifBtn) {
        drawer.classList.add('hidden');
      }
    });
  }

  function showView(name) {
    $$('.pf-view').forEach((v) => v.classList.toggle('active', v.dataset.view === name));
    $$('.pf-nav a[data-pf]').forEach((a) => a.classList.toggle('active', a.dataset.pf === name));
    $$('.pf-bottom a[data-pf]').forEach((a) => a.classList.toggle('active', a.dataset.pf === name));
    // hide legacy bottom nav conflict when on home sections
    const legacy = document.querySelector('.bottom-nav');
    if (legacy) {
      legacy.style.display = name === 'countries' ? '' : 'none';
    }
  }

  $$('[data-pf]').forEach((el) => {
    el.addEventListener('click', (e) => {
      const name = el.dataset.pf;
      if (!name) return;
      if (el.tagName === 'A' && el.getAttribute('href') && el.getAttribute('href') !== '#') {
        return; // real navigation e.g. /quiz
      }
      e.preventDefault();
      showView(name);
      if (name === 'countries') {
        const nc = document.getElementById('navCountries');
        if (nc) nc.click();
      }
    });
  });

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
                (q) => `
          <a class="pf-card" href="/quiz" style="text-decoration:none;color:inherit">
            <h3>${esc(q.title)}</h3>
            <p>${esc(q.description || (q.questionCount || 0) + ' савол')}</p>
            <span class="pf-tag">Викторина · ҳад ${q.passScore || 70}%</span>
          </a>`
              )
              .join('')
          : `<div class="pf-card"><h3>Викторинаҳо</h3><p>Ҳоло рӯйхат холӣ аст. Аз /quiz кушоед.</p></div>`;
      }
      const oBox = $('#pfUpcomingOly');
      if (oBox) {
        const list = (oly.olympiads || []).slice(0, 4);
        oBox.innerHTML = list.length
          ? list
              .map(
                (o) => `
          <a class="pf-card" href="/student" style="text-decoration:none;color:inherit">
            <h3>${esc(o.title)}</h3>
            <p>${o.questionCount || 0} савол · ҳад ${o.passScore || 70}%</p>
            <span class="pf-tag">${o.type === 'quiz' ? 'Викторина' : 'Олимпиада'}</span>
          </a>`
              )
              .join('')
          : `<div class="pf-card"><h3>Олимпиадаҳо</h3><p>Ҳоло фаъол нест. Воридшавии хонанда: /student</p></div>`;
      }
      const st = $('#pfStatQuizzes');
      if (st) st.textContent = String((quizzes.quizzes || []).length);
      const so = $('#pfStatOlympiads');
      if (so) so.textContent = String((oly.olympiads || []).length);
    } catch (e) {
      console.warn(e);
    }
  }

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  // Google avatar from localStorage if present
  try {
    const u = JSON.parse(localStorage.getItem('geo_user') || localStorage.getItem('currentUser') || 'null');
    const av = $('#pfAvatar');
    if (u && av) {
      if (u.picture) {
        av.innerHTML = `<img src="${u.picture}" alt="" />`;
      } else if (u.name) {
        av.textContent = u.name.trim().slice(0, 1).toUpperCase();
      }
    }
  } catch (_) {}

  loadHomeData();
  showView('home');
})();
