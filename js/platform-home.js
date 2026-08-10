/** Home Live Dashboard — data only (markup is in index.html) */
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

  async function loadData() {
    try {
      const [quizzesRes, olyRes, lbRes] = await Promise.all([
        fetch('/api/quizzes').then((r) => r.json()).catch(() => ({ quizzes: [] })),
        fetch('/api/olympiads/active').then((r) => r.json()).catch(() => ({ olympiads: [] })),
        fetch('/api/leaderboard?limit=3').then((r) => r.json()).catch(() => ({ entries: [] })),
      ]);
      const quizzes = quizzesRes.quizzes || [];
      const olympiads = olyRes.olympiads || [];

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
      if (oBox && olympiads.length) {
        oBox.innerHTML = olympiads
          .slice(0, 5)
          .map(
            (o) => `<div class="pf-act">
            <div>
              <div class="pf-act-main"><strong>${esc(o.title)}</strong></div>
              <div class="pf-act-meta">${o.questionCount || 0} савол · ҳад ${o.passScore || 70}%</div>
            </div>
            <div class="pf-act-time">${o.type === 'quiz' ? 'quiz' : 'olympiad'}</div>
          </div>`
          )
          .join('');
      }

      const feed = document.getElementById('pfActivityFeed');
      if (feed) {
        const rows = [];
        olympiads.slice(0, 4).forEach((o) => rows.push({ title: o.title, meta: 'Олимпиада фаъол' }));
        quizzes.slice(0, 4).forEach((q) => rows.push({ title: q.title, meta: 'Викторина дастрас' }));
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
        const entries = (lbRes && lbRes.entries) || [];
        if (lbRes && lbRes.public === false) {
          lb.innerHTML = `<div class="pf-empty"><div class="ico">🔒</div><span>Пӯшида</span></div>`;
        } else if (entries.length) {
          lb.innerHTML = entries
            .slice(0, 3)
            .map((e, i) => {
              const rank = e.rank || i + 1;
              const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '#' + rank;
              const name = e.name || e.studentName || '—';
              const clean = String(name).replace(/^Gmail\s*[·•\-:]?\s*/i, '').trim() || name;
              return `<div class="pf-lb-row">
                <span class="pf-lb-rank">${medal}</span>
                <span class="pf-lb-name">${esc(clean)}</span>
                <span class="pf-lb-score">${esc(e.rating ?? e.score ?? '—')}</span>
              </div>`;
            })
            .join('');
        } else {
          lb.innerHTML = `<div class="pf-empty"><div class="ico">⭐</div><span data-i18n="lbEmpty">Натиҷаҳо баъд аз супориш</span></div>`;
        }
      }
    } catch (e) {
      console.warn('platform-home', e);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadData);
  else loadData();
})();
