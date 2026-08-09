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

  // Scroll links only — do NOT hide countries app
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

  loadHomeData();
})();
