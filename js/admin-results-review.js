/** gzip loader admin-results-review */
(async function(){
  try {
    const base = (document.currentScript && document.currentScript.src) || '';
    const dir = base.replace(/[^/]+$/, '');
    const n = 2;
    const parts = [];
    for (let i=0;i<n;i++) {
      parts.push(await fetch(dir + '_rr_z' + i + '.txt', {credentials:'same-origin'}).then(r=>r.text()));
    }
    const b64 = parts.join('').replace(/\s+/g,'');
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
    const ds = new DecompressionStream('gzip');
    const stream = new Blob([bytes]).stream().pipeThrough(ds);
    const ab = await new Response(stream).arrayBuffer();
    const code = new TextDecoder().decode(ab);
    const s = document.createElement('script');
    s.textContent = code;
    document.head.appendChild(s);
  } catch(e) { console.error('rr load', e); }
})();
