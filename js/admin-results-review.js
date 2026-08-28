/** admin-results-review — gzip parts */
(async function () {
  try {
    const base = (document.currentScript && document.currentScript.src) || '';
    const dir = base.replace(/[^/]+$/, '');
    const n = 4;
    const chunks = [];
    for (let i = 0; i < n; i++) {
      const t = await fetch(dir + '_rrgz_' + i + '.txt', { credentials: 'same-origin' }).then(r => {
        if (!r.ok) throw new Error('part ' + i + ' ' + r.status);
        return r.text();
      });
      chunks.push(t.trim());
    }
    const b64 = chunks.join('');
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const ds = new DecompressionStream('gzip');
    const stream = new Blob([bytes]).stream().pipeThrough(ds);
    const ab = await new Response(stream).arrayBuffer();
    const code = new TextDecoder().decode(ab);
    const s = document.createElement('script');
    s.textContent = code;
    document.head.appendChild(s);
  } catch (e) {
    console.error('admin-results-review load failed', e);
  }
})();
