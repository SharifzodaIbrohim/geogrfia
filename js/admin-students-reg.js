/* admin-students-reg gzip parts loader */
(function(){
  function b64ToU8(s){var bin=atob(s);var u=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return u;}
  Promise.all([
    fetch("/js/_asr_b64_00.txt",{cache:"no-store"}).then(function(r){return r.text();}),
    fetch("/js/_asr_b64_01.txt",{cache:"no-store"}).then(function(r){return r.text();})
  ]).then(async function(parts){
    var u8=b64ToU8(parts[0]+parts[1]);
    var ds=new DecompressionStream("gzip");
    var stream=new Blob([u8]).stream().pipeThrough(ds);
    var text=await new Response(stream).text();
    var s=document.createElement("script");
    s.textContent=text;
    document.documentElement.appendChild(s);
  }).catch(function(e){console.error("admin-students-reg",e);});
})();
