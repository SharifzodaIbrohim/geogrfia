(function () {
  function tok() {
    return localStorage.getItem('geo_admin_token') || '';
  }
  function hdr(json) {
    var h = {};
    if (json) h['Content-Type'] = 'application/json';
    var t = tok();
    if (t) h['X-Admin-Token'] = t;
    return h;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  async function loadContent() {
    var body = document.getElementById('contentBody');
    if (!body) return;
    body.innerHTML = '<tr><td colspan="5">Бор мешавад…</td></tr>';
    try {
      var res = await fetch('/api/admin/content', {
        headers: hdr(),
        credentials: 'include',
      });
      var d = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(d.error || ('HTTP ' + res.status));
      var rows = d.items || d.content || [];
      body.innerHTML = rows.length
        ? rows
            .map(function (it) {
              return (
                '<tr><td>' +
                esc(it.type || '') +
                '</td><td>' +
                esc(it.title || '') +
                '</td><td>' +
                esc(it.lang || '') +
                '</td><td style="max-width:220px;overflow:hidden;text-overflow:ellipsis">' +
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
            headers: hdr(),
            credentials: 'include',
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
    if (form && !form._cBound) {
      form._cBound = true;
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var msg = document.getElementById('cMsg');
        try {
          var res = await fetch('/api/admin/content', {
            method: 'POST',
            headers: hdr(true),
            credentials: 'include',
            body: JSON.stringify({
              type: document.getElementById('cType').value,
              title: document.getElementById('cTitle').value.trim(),
              description: document.getElementById('cDesc').value.trim(),
              url: document.getElementById('cUrl').value.trim(),
              lang: document.getElementById('cLang').value,
            }),
          });
          var d = await res.json().catch(function () { return {}; });
          if (!res.ok) throw new Error(d.error || 'Хато');
          if (msg) {
            msg.textContent = 'Илова шуд';
            msg.classList.remove('hidden', 'error');
          }
          form.reset();
          loadContent();
        } catch (err) {
          if (msg) {
            msg.textContent = err.message;
            msg.classList.remove('hidden');
            msg.classList.add('error');
          }
        }
      });
    }
    document.querySelectorAll('.tab[data-tab="content"]').forEach(function (btn) {
      if (btn._cBound) return;
      btn._cBound = true;
      btn.addEventListener('click', function () {
        setTimeout(loadContent, 30);
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
