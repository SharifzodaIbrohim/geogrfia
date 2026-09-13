/* Student reg + camera + CSV + folder + Даватнома */
(function () {
  var TOKEN_KEY = "geo_admin_token";
  var DIR_DB = "geografia_admin_fs";
  var DIR_STORE = "handles";
  var DIR_KEY = "students_dir";
  var _camStream = null;
  var _photoDataUrl = null;
  var _studentsLocal = [];
  var _dirHandle = null;

  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }

  function setCamStatus(msg) {
    var el = document.getElementById("cameraStatus");
    if (el) el.textContent = msg || "";
  }

  function fillCameraSelect() {
    var sel = document.getElementById("cameraSelect");
    if (!sel) return;
    navigator.mediaDevices.enumerateDevices().then(function (devs) {
      var cams = devs.filter(function (d) { return d.kind === "videoinput"; });
      if (!cams.length) { sel.innerHTML = '<option value="">Камера ёфт нашуд</option>'; return; }
      sel.innerHTML = "";
      cams.forEach(function (d, i) {
        var o = document.createElement("option");
        o.value = d.deviceId;
        o.textContent = d.label || ("Камера " + (i + 1));
        sel.appendChild(o);
      });
    }).catch(function () { setCamStatus("Камера кам нагашт"); });
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCamStatus("Камера дастгирӣ намешавад (HTTPS лозим)"); return;
    }
    var sel = document.getElementById("cameraSelect");
    var video = document.getElementById("cameraVideo");
    if (!video) return;
    try {
      if (_camStream) { _camStream.getTracks().forEach(function (t) { t.stop(); }); _camStream = null; }
      var constraints = { video: { facingMode: "user" }, audio: false };
      if (sel && sel.value) constraints.video = { deviceId: { exact: sel.value } };
      _camStream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = _camStream;
      await video.play();
      setCamStatus("Камера фаъол");
    } catch (e) {
      setCamStatus("Хато камера: " + (e.message || e));
    }
  }

  function stopCamera() {
    if (_camStream) {
      _camStream.getTracks().forEach(function (t) { t.stop(); });
      _camStream = null;
    }
    var video = document.getElementById("cameraVideo");
    if (video) video.srcObject = null;
    setCamStatus("Камера истод");
  }

  function capturePhoto() {
    var video = document.getElementById("cameraVideo");
    var canvas = document.getElementById("cameraCanvas");
    if (!video || !canvas) return;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);
    _photoDataUrl = canvas.toDataURL("image/jpeg", 0.85);
    setCamStatus("Акс гирифта шуд");
    var prev = document.getElementById("photoPreview");
    if (prev) { prev.src = _photoDataUrl; prev.style.display = "block"; }
  }

  // NOTE: truncated intentionally in this draft - full file follows in next push if needed
