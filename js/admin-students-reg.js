(function(){
  var F=[];
  for (var i=0;i<8;i++) F.push("/js/_asr8_"+i+".js");
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(parts){
    (0,eval)(parts.join(""));
  }).catch(function(e){ console.error("[students-reg] load failed", e); });
})();
