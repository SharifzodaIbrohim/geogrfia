(async function(){
  const parts = [];
  for (let i = 0; i < 4; i++) {
    const r = await fetch('/js/_sgz_' + i + '.txt');
    if (!r.ok) throw new Error('sgz ' + i);
    parts.push(await r.text());
  }
  const b64 = parts.join('').replace(/\s/g, '');
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const ds = new DecompressionStream('gzip');
  const stream = new Response(bin).body.pipeThrough(ds);
  const code = await new Response(stream).text();
  (0, eval)(code);
})().catch(e => console.error('[student.sgz]', e));
