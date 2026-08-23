/* Даватнома print patch — load AFTER admin-students-reg.js */
(function(){
  var CSS = "@page{size:A4;margin:7mm}"+ 
    "@media print{body{background:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}"+ 
    ".toolbar,.hint{display:none!important}.page{margin:0;max-width:none}"+ 
    ".pass{box-shadow:none;border-radius:0;page-break-inside:avoid}"+ 
    ".photo-wrap{width:96px!important;height:96px!important}"+ 
    ".qr img{width:90px!important;height:90px!important}"+ 
    "table{font-size:11.5px!important}th,td{padding:4px 8px!important}"+ 
    ".head{padding:10px 16px 8px!important}.head h1{font-size:1.35rem!important;margin:6px 0 2px!important}"+ 
    ".body{padding:10px 14px 6px!important}.foot{padding:8px 14px 10px!important}"+ 
    ".idbox{font-size:1rem!important;padding:6px 10px!important}}";

  var HINT = '<p class="hint" style="text-align:center;font-size:11px;color:#5a6b62;margin:4px 0 8px">'+
    'Чоп: дар Print → Headers and footers-ро ХОМӮШ кунед (то file:// / суроға наояд)</p>';

  function patchHtml(html){
    if(!html || html.indexOf("Даватнома")<0) return html;
    html = html.replace(/color=c13584/g,"color=000000");
    html = html.replace(/size=160x160/g,"size=120x120");
    if(html.indexOf("@page{size:A4;margin:7mm}")<0){
      html = html.replace("</style>", CSS + "</style>");
    }
    if(html.indexOf("Headers and footers")<0){
      html = html.replace("</div><article", "</div>"+HINT+"<article");
    }
    html = html.replace(/\.photo-wrap\{width:152px;height:152px/g,".photo-wrap{width:96px;height:96px");
    html = html.replace(/\.qr img\{width:150px;height:150px/g,".qr img{width:95px;height:95px");
    return html;
  }

  var OrigBlob = window.Blob;
  window.Blob = function(parts, opts){
    try {
      if(parts && parts.length===1 && typeof parts[0]==="string" && parts[0].indexOf("Даватнома")>=0){
        parts = [patchHtml(parts[0])];
      }
    } catch(_){}
    return new OrigBlob(parts, opts);
  };
  window.Blob.prototype = OrigBlob.prototype;

  console.log("[davotnoma-print] patch installed");
})();
