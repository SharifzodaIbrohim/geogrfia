(function(){
  var F=["/js/admin-students-reg-body-a.js","/js/admin-students-reg-body-b.js"];
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(parts){
    var out = parts.join("");
    (0,eval)(out);
  }).catch(function(e){ console.error("[students-reg] load failed", e); });
})();
