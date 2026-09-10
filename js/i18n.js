/** i18n raw-deflate+b64 loader /js/_i180..9.txt */
(async function () {
  const n = 10;
  const parts = [];
  for (let i = 0; i < n; i++) {
    const r = await fetch('/js/_i18' + i + '.txt');
    if (!r.ok) throw new Error('_i18' + i + ' HTTP ' + r.status);
    parts.push(await r.text());
  }
  let b64 = parts.join('').replace(/\s/g, '');
  const pad = (4 - (b64.length % 4)) % 4;
  if (pad) b64 += '='.repeat(pad);
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const ds = new DecompressionStream('deflate');
  const stream = new Blob([bytes]).stream().pipeThrough(ds);
  const ab = await new Response(stream).arrayBuffer();
  const code = new TextDecoder('utf-8').decode(ab);
  (0, eval)(code);
})().catch(function (e) {
  console.error('[i18n loader]', e);
  if (document.body) document.body.insertAdjacentHTML('beforeend',
    '<pre style="color:#f66;padding:1rem">i18n: ' + (e && e.message) + '</pre>');
});
