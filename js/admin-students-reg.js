(function(){
  var F=["/js/_asr_c0.txt","/js/_asr_c1.txt","/js/_asr_c2.txt","/js/_asr_c3.txt","/js/_asr_c4.txt","/js/_asr_c5.txt","/js/_asr_c6.txt","/js/_asr_c7.txt","/js/_asr_c8.txt","/js/_asr_c9.txt","/js/_asr_c10.txt","/js/_asr_c11.txt"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(p){ (0,eval)(p.join("")); })
  .catch(function(e){ console.error("[students-reg] load failed", e); });
})();
