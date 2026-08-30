(function(){
  fetch("/js/admin-students-reg-body.js",{credentials:"same-origin"})
    .then(function(r){ if(!r.ok) throw new Error("body "+r.status); return r.text(); })
    .then(function(src){ (0,eval)(src); })
    .catch(function(e){ console.error("[students-reg] load failed", e); });
})();
