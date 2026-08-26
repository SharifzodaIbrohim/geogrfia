/** Load full admin-results-review.js from base64 parts */
(async function () {
  try {
    const base = (document.currentScript && document.currentScript.src) || '';
    const dir = base.replace(/[^/]+$/, '');
    const n = 10;
    const chunks = [];
    for (let i = 0; i < n; i++) {
      const id = String(i).padStart(2, '0');
      const t = await fetch(dir + '_rrj_b64_' + id + '.txt', { credentials: 'same-origin' }).then(r => {
        if (!r.ok) throw new Error('part ' + id + ' ' + r.status);
        return r.text();
      });
      chunks.push(t.trim());
    }
    const bin = atob(chunks.join(''));
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const code = new TextDecoder('utf-8').decode(bytes);
    const s = document.createElement('script');
    s.textContent = code;
    document.head.appendChild(s);
  } catch (e) {
    console.error('admin-results-review load failed', e);
  }
})();
