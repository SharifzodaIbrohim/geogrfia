(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function loadContent() {
    var body = document.getElementById('contentBody');
    if (!body) return;
    try {
      var res = await fetch('/api/admin/content', { headers: { 'X-Admin-Token': tok() } });
      var d = await res.json();
      var rows = d.items || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (it) {
              return (
                '<tr><td>' +
                esc(it.type) +
                '</td><td>' +
                esc(it.title) +
                '</td><td>' +
                esc(it.lang || '') +
                '</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">' +
                esc(it.url || '') +
                '</td><td><button type="button" class="btn small" data-del="' +
                esc(it.id) +
                '">✕</button></td></tr>'
              );
            })
            .join('')
        : '<tr><td colspan="5">Холӣ</td></tr>';
      body.querySelectorAll('[data-del]').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          if (!confirm('Нест кунем?')) return;
          await fetch('/api/admin/content/' + btn.getAttribute('data-del'), {
            method: 'DELETE',
            headers: { 'X-Admin-Token': tok() },
          });
          loadContent();
        });
      });
    } catch (e) {
      body.innerHTML = '<tr><td colspan="5">' + esc(e.message) + '</td></tr>';
    }
  }
  function wire() {
    var form = document.getElementById('contentForm');
    if (form) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var msg = document.getElementById('cMsg');
        try {
          var res = await fetch('/api/admin/content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Admin-Token': tok() },
            body: JSON.stringify({
              type: document.getElementById('cType').value,
              title: document.getElementById('cTitle').value.trim(),
              description: document.getElementById('cDesc').value.trim(),
              url: document.getElementById('cUrl').value.trim(),
              lang: document.getElementById('cLang').value,
            }),
          });
          var d = await res.json();
          if (!res.ok) throw new Error(d.error || 'Хато');
          if (msg) {
            msg.textContent = 'Илова шуд';
            msg.classList.remove('hidden');
          }
          form.reset();
          loadContent();
        } catch (err) {
          if (msg) {
            msg.textContent = err.message;
            msg.classList.remove('hidden');
          }
        }
      });
    }
    document.querySelectorAll('.tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (btn.dataset.tab === 'content') loadContent();
        if (btn.dataset.tab === 'gmail') {
          var f = document.getElementById('gmFilter');
          if (f) f.click();
        }
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
