/** _admin_js_ loader */
(async function () {
  const n = 20;
  const parts = [];
  for (let i = 0; i < n; i++) {
    const r = await fetch('/js/_admin_js_' + i + '.txt');
    if (!r.ok) throw new Error('_admin_js_' + i + ' HTTP ' + r.status);
    parts.push(await r.text());
  }
  const b64 = parts.join('').replace(/\s/g, '');
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const code = new TextDecoder('utf-8').decode(bytes);
  (0, eval)(code);
})().catch(function (e) {
  console.error('[_admin_js_ loader]', e);
});
