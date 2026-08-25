/* Даъватнома print + text-fix patch — load AFTER admin-students-reg if present */
(function(){
  var CSS = "@page{size:A4;margin:5mm}"+"@media print{html,body{height:auto!important;overflow:hidden!important;background:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}"+  ".toolbar,.hint{display:none!important}.page{margin:0;padding:0;max-width:none}"+  ".pass{box-shadow:none;border-radius:0;page-break-inside:avoid;break-inside:avoid}"+  ".foot,.body,.head,.qr-row,.top{page-break-inside:avoid;break-inside:avoid}"+  ".photo-wrap{width:68px!important;height:68px!important}"+  ".qr img{width:72px!important;height:72px!important}"+  "table{font-size:10px!important}th,td{padding:2px 5px!important}"+  ".head{padding:5px 10px 4px!important}.head h1{font-size:1.05rem!important;margin:3px 0 1px!important}"+  ".body{padding:5px 8px 3px!important}.foot{padding:4px 8px 5px!important}"+  ".idbox{font-size:.82rem!important;padding:3px 6px!important}"+  ".seal{margin-top:4px!important;font-size:.75rem!important}"+  ".note{margin-top:3px!important;font-size:.65rem!important}}";

  var HINT = '<p class="hint" style="text-align:center;font-size:11px;color:#5a6b62;margin:4px 0 8px">'+    'Чоп: дар Print → <b>Headers and footers</b>-ро ХОМӮШ кунед (то file:// / суроға наояд)</p>';

  function fixTexts(html){
    html = html.replace(/ДАВАТНОМА · ИҶОЗАТНОМА/g, "ДАЪВАТНОМА · ИҶОЗАТНОМА");
    html = html.replace(/<h1>Даватнома<\/h1>/g, "<h1>Даъватнома</h1>");
    html = html.replace(/<title>Даватнома/g, "<title>Даъватнома");
    html = html.replace(/Ҳуҷҷати расмии иштирок дар олимпиада \/ викторина/g, "Ҳуҷҷати расмӣ иштирокҷи дар олимпиада");
    html = html.replace(/Ҳуҷҷати расмии бақайдгирӣ барои олимпиада \/ викторина/g, "Ҳуҷҷати расмӣ иштирокҷи дар олимпиада");
    html = html.replace(/ID барои воридшавӣ/g, "ID-и иштирокчӣ");
    html = html.replace(/ID \(барои воридшавӣ\)/g, "ID-и иштирокчӣ");
    html = html.replace(/ID БАРОИ ВОРИДШАВӢ/g, "ID-И ИШТИРОКЧӢ");
    html = html.replace(/Санаи оғоз:/g, "Санаи имтиҳонсупори:");
    html = html.replace(/>Муассиса \/ Мактаб</g, ">Муассисаи таълимӣ<");
    html = html.replace(/>Синф</g, ">Синфӣ<");
    html = html.replace(/>Унвони олимпиада</g, ">Намуди олимпиада<");
    html = html.replace(
      /Ин даватнома ҳуҷҷати расмии иштирок аст\. ID-ро нигоҳ доред ва барои воридшавӣ ба платформа истифода баред\./g,
      "Ин даватнома ҳуҷҷати расмии иштиррок аст."
    );
    return html;
  }

  function patchHtml(html){
    if(!html || (html.indexOf("Даъватнома")<0 && html.indexOf("Даватнома")<0)) return html;
    html = fixTexts(html);
    html = html.replace(/color=c13584/g,"color=000000");
    html = html.replace(/size=160x160/g,"size=120x120");
    if(html.indexOf("@page{size:A4;margin:5mm}")<0){
      html = html.replace("</style>", CSS + "</style>");
    }
    if(html.indexOf("Headers and footers")<0){
      html = html.replace("</div><article", "</div>"+HINT+"<article");
    }
    html = html.replace(/\.photo-wrap\{width:152px;height:152px/g,".photo-wrap{width:72px;height:72px");
    html = html.replace(/\.photo-wrap\{width:96px;height:96px/g,".photo-wrap{width:72px;height:72px");
    html = html.replace(/\.qr img\{width:150px;height:150px/g,".qr img{width:78px;height:78px");
    html = html.replace(/\.qr img\{width:95px;height:95px/g,".qr img{width:78px;height:78px");
    return html;
  }

  var OrigBlob = window.Blob;
  window.Blob = function(parts, opts){
    try {
      if(parts && parts.length===1 && typeof parts[0]==="string" && (parts[0].indexOf("Даъватнома")>=0 || parts[0].indexOf("Даватнома")>=0)){
        parts = [patchHtml(parts[0])];
      }
    } catch(_){}
    return new OrigBlob(parts, opts);
  };
  window.Blob.prototype = OrigBlob.prototype;

  console.log("[davotnoma-print] text-fix + compact 1-page + black IG installed");
})();
