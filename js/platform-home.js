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
      const [quizzesRes, olyRes] = await Promise.all([
        fetch('/api/quizzes').then((r) => r.json()).catch(() => ({ quizzes: [] })),
        fetch('/api/olympiads/active').then((r) => r.json()).catch(() => ({ olympiads: [] })),
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
      if (lb && olympiads[0] && olympiads[0].id) {
        try {
          const d = await fetch('/api/olympiads/' + olympiads[0].id + '/leaderboard').then((r) => r.json());
          const entries = d.entries || d.leaderboard || [];
          if (entries.length) {
            lb.innerHTML = entries
              .slice(0, 7)
              .map(
                (e, i) => `<div class="pf-lb-row">
                <span class="pf-lb-rank">#${e.rank || i + 1}</span>
                <span class="pf-lb-name">${esc(e.studentName || e.name || '—')}</span>
                <span class="pf-lb-score">${e.score ?? '—'}</span>
              </div>`
              )
              .join('');
          }
        } catch (_) {}
      }
    } catch (e) {
      console.warn('platform-home', e);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadData);
  else loadData();
})();
