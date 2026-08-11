(() => {
  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }
  function set(id, v) {
    const el = document.getElementById(id);
    if (el) el.textContent = v;
  }

  async function loadHome() {
    try {
      const [quizzesRes, olyRes, lbRes] = await Promise.all([
        fetch('/api/quizzes').then((r) => r.json()).catch(() => ({ quizzes: [] })),
        fetch('/api/olympiads/active').then((r) => r.json()).catch(() => ({ olympiads: [] })),
        fetch('/api/leaderboard?limit=3').then((r) => r.json()).catch(() => ({ entries: [] })),
      ]);

      const quizzesRaw = quizzesRes.quizzes || [];
      const olympiadsRaw = olyRes.olympiads || [];

      // Pure olympiads only (exclude type=quiz — those belong under quizzes)
      const olympiads = [];
      const seenO = new Set();
      for (const o of olympiadsRaw) {
        const id = String(o.id || '');
        if (!id || seenO.has(id)) continue;
        if ((o.type || 'olympiad').toLowerCase() === 'quiz') continue;
        seenO.add(id);
        olympiads.push(o);
      }

      // Quizzes: only /api/quizzes, deduped by id
      const quizzes = [];
      const seenQ = new Set();
      for (const q of quizzesRaw) {
        const id = String(q.id || '');
        if (!id || seenQ.has(id)) continue;
        seenQ.add(id);
        quizzes.push(q);
      }

      set('pfMQuizzes', String(quizzes.length));
      set('pfMOlympiads', String(olympiads.length));
      set('pfMCountries', '195+');

      const qBox = document.getElementById('pfFeaturedQuizzes');
      if (qBox) {
        const list = quizzes.slice(0, 6);
        qBox.innerHTML = list.length
          ? list
              .map(
                (q) => `<a class="pf-card" href="/quiz">
            <h3>${esc(q.title)}</h3>
            <p>${esc(q.description || (q.questionCount || 0) + ' савол')}</p>
            <span class="pf-tag">Ҳад ${q.passScore || 70}%</span>
          </a>`
              )
              .join('')
          : `<div class="pf-card"><h3>Викторинаҳо</h3><p>Ҳоло холӣ — аз /quiz кушоед.</p></div>`;
      }

      const oBox = document.getElementById('pfUpcomingBox');
      if (oBox) {
        if (olympiads.length) {
          oBox.innerHTML = olympiads
            .slice(0, 5)
            .map(
              (o) => `<div class="pf-act">
            <div>
              <div class="pf-act-main"><strong>${esc(o.title)}</strong></div>
              <div class="pf-act-meta">${o.questionCount || 0} савол · ҳад ${o.passScore || 70}%</div>
            </div>
            <div class="pf-act-time">olympiad</div>
          </div>`
            )
            .join('');
        }
      }

      const feed = document.getElementById('pfActivityFeed');
      if (feed) {
        const rows = [];
        const seenFeed = new Set();
        olympiads.slice(0, 4).forEach((o) => {
          const id = String(o.id || o.title);
          if (seenFeed.has(id)) return;
          seenFeed.add(id);
          rows.push({ title: o.title, meta: 'Олимпиада фаъол' });
        });
        quizzes.slice(0, 4).forEach((q) => {
          const id = String(q.id || q.title);
          if (seenFeed.has(id)) return;
          seenFeed.add(id);
          rows.push({ title: q.title, meta: 'Викторина дастрас' });
        });
        if (rows.length) {
          feed.innerHTML = rows
            .slice(0, 8)
            .map(
              (r) => `<div class="pf-act">
              <div>
                <div class="pf-act-main"><span class="ok">●</span> <strong>${esc(r.title)}</strong></div>
                <div class="pf-act-meta">${esc(r.meta)}</div>
              </div>
              <div class="pf-act-time">ҳоло</div>
            </div>`
            )
            .join('');
        }
      }

      const lb = document.getElementById('pfLeaderPreview');
      if (lb) {
        const entries = lbRes.entries || lbRes.leaders || [];
        if (entries.length) {
          lb.innerHTML = entries
            .slice(0, 3)
            .map(
              (e, i) => `<div class="pf-act">
              <div class="pf-act-main"><strong>${i + 1}. ${esc(e.name || e.studentName || '—')}</strong></div>
              <div class="pf-act-time">${e.score ?? e.points ?? '—'}</div>
            </div>`
            )
            .join('');
        }
      }
    } catch (err) {
      console.warn('[platform-home]', err);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadHome);
  } else {
    loadHome();
  }
})();
