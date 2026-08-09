/** Phase 19 — Home Live Dashboard (product UI) */
(() => {
  const $ = (s, r = document) => r.querySelector(s);

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function mountHomeShell() {
    const host = document.getElementById('pfHome');
    if (!host) return;

    host.innerHTML = `
      <div class="pf-dash">
        <p class="pf-kicker">Platform activity</p>
        <h1 class="pf-dash-title">Live Dashboard</h1>

        <div class="pf-metrics">
          <div>
            <span class="pf-metric-label">Кишварҳо</span>
            <span class="pf-metric-value" id="pfMCountries">—</span>
          </div>
          <div>
            <span class="pf-metric-label">Викторинаҳо</span>
            <span class="pf-metric-value" id="pfMQuizzes">—</span>
          </div>
          <div>
            <span class="pf-metric-label">Хонандагон</span>
            <span class="pf-metric-value" id="pfMStudents">—</span>
          </div>
          <div>
            <span class="pf-metric-label">Олимпиадаҳо</span>
            <span class="pf-metric-value" id="pfMOlympiads">—</span>
          </div>
        </div>

        <div class="pf-workspace">
          <div class="pf-panel">
            <div class="pf-panel-head">
              <div class="pf-panel-title">
                <span class="pf-dots" aria-hidden="true"><i></i><i></i><i></i></span>
                results.log
                <span class="pf-live-badge">live</span>
              </div>
              <span style="color:var(--pf-faint);font-size:0.75rem">навсозӣ</span>
            </div>
            <div class="pf-panel-body" id="pfActivityFeed">
              <div class="pf-empty"><div class="ico">📡</div>Фаъолият ҳоло нест</div>
            </div>
          </div>

          <div class="pf-side">
            <div class="pf-panel">
              <div class="pf-panel-head">
                <h2>🏅 Олимпиадаҳо</h2>
                <a href="/student">Ҳама →</a>
              </div>
              <div class="pf-panel-body" id="pfUpcomingBox">
                <div class="pf-empty"><div class="ico">🏆</div>Фаъол нест<br><a href="/student">Воридшавии хонанда</a></div>
              </div>
            </div>
            <div class="pf-panel">
              <div class="pf-panel-head">
                <h2>Leaderboard</h2>
                <a href="/quiz">View</a>
              </div>
              <div class="pf-panel-body" id="pfLeaderPreview">
                <div class="pf-empty"><div class="ico">⭐</div>Натиҷаҳо баъдтар</div>
              </div>
            </div>
          </div>
        </div>

        <div class="pf-feat-wrap">
          <div class="pf-section-head">
            <h2>Викторинаҳои пешниҳодшуда</h2>
            <a class="more" href="/quiz">Ҳама →</a>
          </div>
          <div class="pf-feat-grid" id="pfFeaturedQuizzes"></div>
        </div>
      </div>
    `;

    // label before countries block
    const countriesSec = document.querySelector('section.pf-view[data-view="countries"], #countries');
    if (countriesSec && !document.querySelector('.pf-countries-label')) {
      const lab = document.createElement('div');
      lab.className = 'pf-countries-label';
      lab.textContent = 'Countries explorer';
      countriesSec.parentNode.insertBefore(lab, countriesSec);
    }
  }

  async function loadData() {
    try {
      const [quizzesRes, olyRes, healthRes] = await Promise.all([
        fetch('/api/quizzes').then((r) => r.json()).catch(() => ({ quizzes: [] })),
        fetch('/api/olympiads/active').then((r) => r.json()).catch(() => ({ olympiads: [] })),
        fetch('/api/health').then((r) => r.json()).catch(() => ({})),
      ]);

      const quizzes = quizzesRes.quizzes || [];
      const olympiads = olyRes.olympiads || [];

      const set = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = v;
      };
      set('pfMQuizzes', String(quizzes.length));
      set('pfMOlympiads', String(olympiads.length));
      set('pfMCountries', '195+');

      // try public stats if any
      if (healthRes && healthRes.stats) {
        if (healthRes.stats.students != null) set('pfMStudents', String(healthRes.stats.students));
      }

      // Featured quizzes
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

      // Upcoming olympiads panel
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
              <div class="pf-act-time">${o.type === 'quiz' ? 'quiz' : 'olympiad'}</div>
            </div>`
            )
            .join('');
        }
      }

      // Activity feed from olympiad list as placeholder + quiz titles
      const feed = document.getElementById('pfActivityFeed');
      if (feed) {
        const rows = [];
        olympiads.slice(0, 4).forEach((o) => {
          rows.push({
            title: o.title,
            meta: 'Олимпиада фаъол',
            ok: true,
          });
        });
        quizzes.slice(0, 4).forEach((q) => {
          rows.push({
            title: q.title,
            meta: 'Викторина дастрас',
            ok: true,
          });
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

      // Leaderboard preview: use first olympiad if API exists
      const lb = document.getElementById('pfLeaderPreview');
      if (lb && olympiads[0] && olympiads[0].id) {
        try {
          const d = await fetch('/api/olympiads/' + olympiads[0].id + '/leaderboard').then((r) =>
            r.json()
          );
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

  // theme / notif / avatar from platform.js may already bind;
  // ensure home shell
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      mountHomeShell();
      loadData();
    });
  } else {
    mountHomeShell();
    loadData();
  }
})();
