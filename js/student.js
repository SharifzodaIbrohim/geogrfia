(async function(){
  const b64 = "PLACEHOLDER";
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const ds = new DecompressionStream("gzip");
  const stream = new Response(bin).body.pipeThrough(ds);
  const code = await new Response(stream).text();
  (0, eval)(code);
})().catch(e => console.error("[student.gz]", e));
