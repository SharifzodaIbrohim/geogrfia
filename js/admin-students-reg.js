/* Student reg + camera + CSV + folder + Даъватнома */
(function () {
  var TOKEN_KEY = "geo_admin_token";
  var DIR_DB = "geografia_admin_fs";
  var DIR_STORE = "handles";
  var DIR_KEY = "students_dir";
  var _camStream = null;
  var _dirHandle = null;

  function token() {
    try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }
  function authHeaders() {
    var t = token();
    return t ? { "Authorization": "Bearer " + t, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
  }
  function val(id) {
    var el = document.getElementById(id);
    return el ? (el.value || "").trim() : "";
  }
  function setVal(id, v) {
    var el = document.getElementById(id);
    if (el) el.value = v == null ? "" : String(v);
  }
  function onClick(id, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  }
  function showMsg(msg, isErr) {
    var el = document.getElementById("stRegMsg");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = isErr ? "#c00" : "#0a0";
  }

  /* ---- Camera ---- */
  function setCamStatus(t) {
    var el = document.getElementById("cameraStatus");
    if (el) el.textContent = t || "";
  }
  async function listCameras() {
    var sel = document.getElementById("cameraSelect");
    if (!sel || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
      var devices = await navigator.mediaDevices.enumerateDevices();
      var cams = devices.filter(function (d) { return d.kind === "videoinput"; });
      sel.innerHTML = "";
      if (!cams.length) {
        sel.innerHTML = "<option value=\"\">Камера нест</option>";
        return;
      }
      cams.forEach(function (c, i) {
        var o = document.createElement("option");
        o.value = c.deviceId;
        o.textContent = c.label || ("Камера " + (i + 1));
        sel.appendChild(o);
      });
    } catch (e) {
      setCamStatus("Рӯйхати камера: " + (e.message || e));
    }
  }
  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCamStatus("Камера дастгирӣ намешавад (HTTPS лозим)"); return;
    }
    stopCamera();
    var sel = document.getElementById("cameraSelect");
    var video = document.getElementById("cameraVideo");
    if (!video) return;
    var constraints = { video: { facingMode: "user" }, audio: false };
    if (sel && sel.value) constraints.video = { deviceId: { exact: sel.value } };
    var tries = [constraints, { video: true, audio: false }];
    var lastErr = null;
    for (var i = 0; i < tries.length; i++) {
      try {
        _camStream = await navigator.mediaDevices.getUserMedia(tries[i]);
        video.srcObject = _camStream;
        video.style.display = "block";
        setCamStatus("Камера фаъол");
        await listCameras();
        return;
      } catch (e) {
        lastErr = e;
      }
    }
    setCamStatus("Хато: " + (lastErr && (lastErr.message || lastErr.name) || "getUserMedia"));
  }
  function stopCamera() {
    if (_camStream) {
      try {
        _camStream.getTracks().forEach(function (t) { t.stop(); });
      } catch (e) {}
      _camStream = null;
    }
    var video = document.getElementById("cameraVideo");
    if (video) {
      video.srcObject = null;
      video.style.display = "none";
    }
    setCamStatus("");
  }
  function capturePhoto() {
    var video = document.getElementById("cameraVideo");
    var canvas = document.getElementById("cameraCanvas");
    var preview = document.getElementById("stPhotoPreview");
    var hidden = document.getElementById("stPhotoData");
    if (!video || !canvas || !video.srcObject) {
      setCamStatus("Аввал камераро кушоед"); return;
    }
    var w = video.videoWidth || 640;
    var h = video.videoHeight || 480;
    canvas.width = w;
    canvas.height = h;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    var dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    if (hidden) hidden.value = dataUrl;
    if (preview) {
      preview.src = dataUrl;
      preview.style.display = "block";
    }
    setCamStatus("Акс гирифта шуд");
  }
  function clearPhoto() {
    var hidden = document.getElementById("stPhotoData");
    var preview = document.getElementById("stPhotoPreview");
    if (hidden) hidden.value = "";
    if (preview) {
      preview.removeAttribute("src");
      preview.style.display = "none";
    }
    setCamStatus("Акс пок шуд");
  }

  /* ---- Folder (File System Access) ---- */
  function openDb() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DIR_DB, 1);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(DIR_STORE)) db.createObjectStore(DIR_STORE);
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }
  async function saveDirHandle(h) {
    try {
      var db = await openDb();
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(DIR_STORE, "readwrite");
        tx.objectStore(DIR_STORE).put(h, DIR_KEY);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    } catch (e) {}
  }
  async function loadDirHandle() {
    try {
      var db = await openDb();
      return new Promise(function (resolve) {
        var tx = db.transaction(DIR_STORE, "readonly");
        var req = tx.objectStore(DIR_STORE).get(DIR_KEY);
        req.onsuccess = function () { resolve(req.result || null); };
        req.onerror = function () { resolve(null); };
      });
    } catch (e) { return null; }
  }
  async function ensureDirPermission(h) {
    if (!h) return false;
    try {
      var q = await h.queryPermission({ mode: "readwrite" });
      if (q === "granted") return true;
      var r = await h.requestPermission({ mode: "readwrite" });
      return r === "granted";
    } catch (e) { return false; }
  }
  async function pickFolder() {
    if (!window.showDirectoryPicker) {
      showMsg("Браузер папка интихоб намекунад (Chrome/Edge лозим)", true);
      return;
    }
    try {
      var h = await window.showDirectoryPicker({ mode: "readwrite" });
      _dirHandle = h;
      await saveDirHandle(h);
      showMsg("Папка интихоб шуд: " + (h.name || ""));
    } catch (e) {
      if (e && e.name !== "AbortError") showMsg("Папка: " + (e.message || e), true);
    }
  }
  async function writeFileToDir(name, blob) {
    if (!_dirHandle) {
      _dirHandle = await loadDirHandle();
    }
    if (!_dirHandle || !(await ensureDirPermission(_dirHandle))) {
      return false;
    }
    try {
      var fh = await _dirHandle.getFileHandle(name, { create: true });
      var w = await fh.createWritable();
      await w.write(blob);
      await w.close();
      return true;
    } catch (e) {
      console.warn("[students-reg] writeFile", e);
      return false;
    }
  }

  /* ---- CSV / Excel helpers ---- */
  function csvEscape(s) {
    s = String(s == null ? "" : s);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }
  function downloadBlob(blob, filename) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 500);
  }

  /* ---- Register student ---- */
  async function registerStudent() {
    showMsg("");
    var fullName = val("stFullName");
    var school = val("stSchool");
    var region = val("stRegion");
    var className = val("stClass");
    var gender = val("stGender");
    var phone = val("stPhone");
    var olympiadTitle = val("stOlympiadTitle");
    var olympiadStart = val("stOlympiadStart");
    var photoData = val("stPhotoData");

    if (!fullName) { showMsg("Номи пурра лозим", true); return; }

    var body = {
      fullName: fullName,
      school: school,
      region: region,
      className: className,
      gender: gender,
      phone: phone,
      olympiadTitle: olympiadTitle,
      olympiadStart: olympiadStart,
      photo: photoData || null
    };

    try {
      var res = await fetch("/api/admin/students", {
        method: "POST",
        headers: authHeaders(),
        credentials: "include",
        body: JSON.stringify(body)
      });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        showMsg(data.error || data.message || ("Хато " + res.status), true);
        return;
      }
      var code = data.code || data.studentCode || data.id || "";
      showMsg("Сабт шуд. ID: " + code);

      /* Даъватнома */
      if (typeof window.printDavotnoma === "function") {
        try {
          window.printDavotnoma({
            fullName: fullName,
            school: school,
            region: region,
            className: className,
            gender: gender,
            phone: phone,
            code: code,
            olympiadTitle: olympiadTitle,
            olympiadStart: olympiadStart,
            photo: photoData
          });
        } catch (e) {
          console.warn("[students-reg] davotnoma", e);
        }
      }

      /* optional save photo to folder */
      if (photoData && photoData.indexOf("data:") === 0 && code) {
        try {
          var b64 = photoData.split(",")[1];
          var bin = atob(b64);
          var arr = new Uint8Array(bin.length);
          for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
          var blob = new Blob([arr], { type: "image/jpeg" });
          var fname = (code + "_" + fullName.replace(/\s+/g, "_") + ".jpg").slice(0, 80);
          await writeFileToDir(fname, blob);
        } catch (e) {}
      }

      /* clear form partially */
      setVal("stFullName", "");
      setVal("stPhone", "");
      clearPhoto();
      if (typeof window.loadStudents === "function") {
        try { window.loadStudents(); } catch (e) {}
      }
    } catch (e) {
      showMsg("Шабака: " + (e.message || e), true);
    }
  }

  /* ---- Export CSV ---- */
  async function exportCsv() {
    try {
      var res = await fetch("/api/admin/students", {
        headers: authHeaders(),
        credentials: "include"
      });
      if (!res.ok) { showMsg("Export хато " + res.status, true); return; }
      var list = await res.json();
      if (!Array.isArray(list)) list = list.students || list.items || [];
      var rows = [["code", "fullName", "school", "region", "class", "gender", "phone", "olympiadTitle", "olympiadStart"]];
      list.forEach(function (s) {
        rows.push([
          s.code || s.studentCode || s.id || "",
          s.fullName || s.name || "",
          s.school || s.schoolName || "",
          s.region || "",
          s.className || s.class || "",
          s.gender || "",
          s.phone || "",
          s.olympiadTitle || "",
          s.olympiadStart || ""
        ].map(csvEscape));
      });
      var csv = rows.map(function (r) { return r.join(","); }).join("\n");
      var blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
      downloadBlob(blob, "students_" + new Date().toISOString().slice(0, 10) + ".csv");
      showMsg("CSV зеркашӣ шуд (" + list.length + ")");
    } catch (e) {
      showMsg("CSV: " + (e.message || e), true);
    }
  }

  function bind() {
    console.log("[students-reg] bind OK");
    onClick("btnStartCamera", startCamera);
    onClick("btnCapturePhoto", capturePhoto);
    onClick("btnStopCamera", stopCamera);
    onClick("btnClearPhoto", clearPhoto);
    onClick("btnRegStudent", registerStudent);
    onClick("btnExportStudents", exportCsv);
    onClick("btnPickFolder", pickFolder);
    var camSel = document.getElementById("cameraSelect");
    if (camSel) {
      camSel.addEventListener("change", function () {
        if (_camStream) startCamera();
      });
    }
    /* restore folder handle quietly */
    loadDirHandle().then(function (h) {
      if (h) _dirHandle = h;
    });
    listCameras();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
