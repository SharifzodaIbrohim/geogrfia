/* Student registration + camera + local download */
(function () {
  const TOKEN_KEY = "geo_admin_token";
  const DIR_DB = "geografia_admin_fs";
  const DIR_STORE = "handles";
  const DIR_KEY = "students_info_dir";
  const FOLDER_HINT = "Малумотхои хонандагон";
  var _regLock = false;
  var _dirMemory = null;
  var _camStream = null;

  const esc = window.esc || function (s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  };

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem("adminToken") || "";
  }

  async function api(path, options) {
    options = options || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = getToken();
    if (token) headers["X-Admin-Token"] = token;
    const res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: "include" }));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.message || "Хато");
    return data;
  }

  function clearPhoto() {
    var hidden = document.getElementById("stPhotoData");
    var img = document.getElementById("photoImg");
    var ph = document.getElementById("photoPlaceholder");
    var file = document.getElementById("photoFileInput");
    if (hidden) hidden.value = "";
    if (img) { img.removeAttribute("src"); img.style.display = "none"; }
    if (ph) ph.style.display = "";
    if (file) file.value = "";
  }

  function applyPhoto(dataUrl) {
    var hidden = document.getElementById("stPhotoData");
    var img = document.getElementById("photoImg");
    var ph = document.getElementById("photoPlaceholder");
    if (hidden) hidden.value = dataUrl || "";
    if (img && dataUrl) { img.src = dataUrl; img.style.display = "block"; }
    if (ph) ph.style.display = dataUrl ? "none" : "";
  }

  function camStatus(msg, isErr) {
    var el = document.getElementById("cameraStatus");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = isErr ? "#ff8a8a" : "#8fd4a8";
    el.style.fontWeight = isErr ? "600" : "500";
  }

  function secureContextOk() {
    return !!(window.isSecureContext || location.protocol === "https:" || location.hostname === "localhost");
  }

  async function listCameras() {
    var sel = document.getElementById("cameraSelect");
    if (!sel) return [];
    if (!secureContextOk()) {
      sel.innerHTML = '<option value="">HTTPS лозим аст</option>';
      camStatus("Камера фақат бо HTTPS кор мекунад", true);
      return [];
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      sel.innerHTML = '<option value="">Дастгирӣ намешавад</option>';
      camStatus("Браузер камераро дастгирӣ намекунад (Chrome/Edge)", true);
      return [];
    }
    try {
      try {
        var tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        tmp.getTracks().forEach(function (t) { t.stop(); });
      } catch (permErr) {
        camStatus("Иҷозаи камера: " + (permErr.name || permErr.message || permErr) + " — Allow-ро пахш кунед", true);
      }
      var devices = await navigator.mediaDevices.enumerateDevices();
      var cams = devices.filter(function (d) { return d.kind === "videoinput"; });
      sel.innerHTML = "";
      if (!cams.length) {
        sel.innerHTML = '<option value="">Камера ёфт нашуд</option>';
        camStatus("Камера ёфт нашуд. Windows: Settings → Privacy → Camera → Allow apps", true);
        return [];
      }
      cams.forEach(function (d, i) {
        var opt = document.createElement("option");
        opt.value = d.deviceId || "";
        opt.textContent = d.label || ("Камера " + (i + 1));
        sel.appendChild(opt);
      });
      camStatus(cams.length + " камера омода — «Камера»-ро пахш кунед", false);
      return cams;
    } catch (e) {
      sel.innerHTML = '<option value="">Хато</option>';
      camStatus("Рӯйхати камера: " + (e.message || e), true);
      return [];
    }
  }

  async function startCamera() {
    var video = document.getElementById("cameraVideo");
    var sel = document.getElementById("cameraSelect");
    if (!video) {
      camStatus("video элемент нест — Ctrl+F5", true);
      return;
    }
    if (!secureContextOk()) {
      camStatus("HTTPS лозим аст", true);
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      camStatus("getUserMedia нест", true);
      return;
    }
    if (sel && (!sel.options.length || (sel.options.length === 1 && !sel.value))) {
      await listCameras();
    }
    stopCamera();
    var attempts = [];
    if (sel && sel.value) {
      attempts.push({ audio: false, video: { deviceId: { exact: sel.value }, width: { ideal: 640 }, height: { ideal: 480 } } });
      attempts.push({ audio: false, video: { deviceId: sel.value } });
    }
    attempts.push({ audio: false, video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } } });
    attempts.push({ audio: false, video: true });
    var lastErr = null;
    for (var i = 0; i < attempts.length; i++) {
      try {
        _camStream = await navigator.mediaDevices.getUserMedia(attempts[i]);
        video.srcObject = _camStream;
        video.style.display = "block";
        video.setAttribute("playsinline", "true");
        video.muted = true;
        try { await video.play(); } catch (_) {}
        try { await listCameras(); } catch (_) {}
        camStatus("Камера фаъол — «Акс»-ро пахш кунед", false);
        return;
      } catch (e) { lastErr = e; }
    }
    var name = (lastErr && lastErr.name) || "";
    var msg = (lastErr && lastErr.message) || String(lastErr || "хато");
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      camStatus("Иҷоза рад шуд. 🔒 → Camera → Allow, баъд боз «Камера»", true);
    } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      camStatus("Камера пайдо нашуд. Windows Privacy → Camera → Allow", true);
    } else if (name === "NotReadableError" || name === "TrackStartError") {
      camStatus("Камера банд аст (Zoom/Teams). Банд кунед ва боз кӯшиш кунед", true);
    } else {
      camStatus("Камера: " + name + " " + msg, true);
    }
  }

  function stopCamera() {
    var video = document.getElementById("cameraVideo");
    if (_camStream) {
      try { _camStream.getTracks().forEach(function (t) { t.stop(); }); } catch (_) {}
      _camStream = null;
    }
    if (video) {
      try { video.srcObject = null; } catch (_) {}
      video.style.display = "none";
    }
  }

  function capturePhoto() {
    var video = document.getElementById("cameraVideo");
    var canvas = document.getElementById("cameraCanvas");
    if (!video || !canvas) return;
    if (!video.srcObject || video.videoWidth < 2) {
      camStatus("Аввал «Камера» — то тасвир пайдо шавад", true);
      return;
    }
    var w = video.videoWidth || 640, h = video.videoHeight || 480;
    var scale = Math.min(1, 800 / Math.max(w, h));
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    applyPhoto(canvas.toDataURL("image/jpeg", 0.85));
    camStatus("Акс гирифта шуд ✓", false);
  }

  function bindCamera() {
    var a = document.getElementById("btnStartCamera");
    var b = document.getElementById("btnCapturePhoto");
    var c = document.getElementById("btnClearPhoto");
    var d = document.getElementById("btnStopCamera");
    var f = document.getElementById("photoFileInput");
    var s = document.getElementById("cameraSelect");
    if (a) { a.type = "button"; a.onclick = function (e) { e.preventDefault(); startCamera(); }; }
    if (b) { b.type = "button"; b.onclick = function (e) { e.preventDefault(); capturePhoto(); }; }
    if (c) { c.type = "button"; c.onclick = function (e) { e.preventDefault(); clearPhoto(); stopCamera(); camStatus("Сурат пок шуд", false); }; }
    if (d) { d.type = "button"; d.onclick = function (e) { e.preventDefault(); stopCamera(); camStatus("Камера қатъ", false); }; }
    if (f) {
      f.onchange = function (ev) {
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;
        if (file.size > 4 * 1024 * 1024) { camStatus("Файл хеле калон (макс 4MB)", true); return; }
        var r = new FileReader();
        r.onload = function () { applyPhoto(r.result); camStatus("Аз файл ✓", false); };
        r.onerror = function () { camStatus("Хониши файл хато", true); };
        r.readAsDataURL(file);
      };
    }
    if (s) s.onchange = function () { if (_camStream) startCamera(); };
    listCameras().catch(function (e) {
      camStatus("listCameras: " + (e && e.message ? e.message : e), true);
    });
  }

  function forceDownload(filename, text, mime) {
    try {
      var blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = filename; a.style.display = "none";
      document.body.appendChild(a); a.click();
      setTimeout(function () { try { URL.revokeObjectURL(url); } catch (_) {} a.remove(); }, 1500);
      return true;
    } catch (e) { return false; }
  }

  function safeFileName(s) {
    return String(s || "student").replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_").slice(0, 80);
  }

  function buildStudentCardHtml(st) {
    var id = st.id || "";
    var full = st.fullName || [st.lastName, st.firstName, st.patronymic].filter(Boolean).join(" ");
    var photo = st.photoData || "";
    var photoBlock = photo
      ? "<img src=\"" + photo + "\" style=\"width:140px;height:140px;object-fit:cover;border-radius:8px\"/>"
      : "<div style=\"width:140px;height:140px;border:1px dashed #aaa\">Бе сурат</div>";
    var rows = [["ID", id],["Насаб", st.lastName||""],["Ном", st.firstName||""],["Номи падар", st.patronymic||""],["Мактаб", st.school||""],["Синф", st.className||""],["Омӯзгор", st.teacher||""]];
    var table = rows.map(function (r) {
      return "<tr><td><b>" + esc(r[0]) + "</b></td><td>" + esc(r[1]) + "</td></tr>";
    }).join("");
    return "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/></head><body><h1>" + esc(full) + "</h1><p>" + esc(id) + "</p>" + photoBlock + "<table>" + table + "</table></body></html>";
  }

  function buildStudentTxt(st) {
    return "ID: " + (st.id||"") + "\nНасаб: " + (st.lastName||"") + "\nНом: " + (st.firstName||"") + "\nМактаб: " + (st.school||"") + "\nСинф: " + (st.className||"") + "\n";
  }

  async function idbOpen() {
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
  async function idbGet(key) {
    try {
      var db = await idbOpen();
      return await new Promise(function (resolve, reject) {
        var r = db.transaction(DIR_STORE, "readonly").objectStore(DIR_STORE).get(key);
        r.onsuccess = function () { resolve(r.result || null); };
        r.onerror = function () { reject(r.error); };
      });
    } catch (_) { return null; }
  }
  async function idbSet(key, val) {
    try {
      var db = await idbOpen();
      await new Promise(function (resolve, reject) {
        var tx = db.transaction(DIR_STORE, "readwrite");
        tx.objectStore(DIR_STORE).put(val, key);
        tx.oncomplete = function () { resolve(); };
        tx.onerror = function () { reject(tx.error); };
      });
    } catch (_) {}
  }

  async function writeFileToDir(dirHandle, fileName, contents, mime) {
    var fh = await dirHandle.getFileHandle(fileName, { create: true });
    var w = await fh.createWritable();
    await w.write(new Blob([contents], { type: mime || "text/plain;charset=utf-8" }));
    await w.close();
  }
  async function tryRestoreDir() {
    if (_dirMemory) return _dirMemory;
    if (!window.showDirectoryPicker) return null;
    try {
      var handle = await idbGet(DIR_KEY);
      if (!handle) return null;
      if ((await handle.queryPermission({ mode: "readwrite" })) === "granted") {
        _dirMemory = handle; return handle;
      }
    } catch (_) {}
    return null;
  }
  async function pickStudentsFolder() {
    if (!window.showDirectoryPicker) { alert("Chrome/Edge лозим."); return null; }
    try {
      var handle = await window.showDirectoryPicker({ id: "geografia-students-info", mode: "readwrite", startIn: "documents" });
      _dirMemory = handle; await idbSet(DIR_KEY, handle); updateFolderStatus(true);
      return handle;
    } catch (e) {
      if (!(e && e.name === "AbortError")) alert("Папка: " + (e && e.message ? e.message : e));
      return null;
    }
  }
  function updateFolderStatus(ok) {
    var el = document.getElementById("localFolderStatus");
    if (!el) return;
    el.textContent = ok ? "Папка пайваст ✓" : "Папка интихоб нашудааст";
  }

  async function saveStudentLocalCopy(st) {
    var html = buildStudentCardHtml(st);
    var txt = buildStudentTxt(st);
    var base = safeFileName((st.lastName || "") + "_" + (st.firstName || "") + "_" + (st.id || "")) || "student";
    forceDownload(base + ".html", html, "text/html;charset=utf-8");
    forceDownload(base + ".txt", txt, "text/plain;charset=utf-8");
    try {
      var dir = _dirMemory || (await tryRestoreDir());
      if (dir) {
        await writeFileToDir(dir, base + ".html", html, "text/html;charset=utf-8");
        await writeFileToDir(dir, base + ".txt", txt, "text/plain;charset=utf-8");
        return { ok: true, mode: "folder+download" };
      }
    } catch (_) {}
    return { ok: true, mode: "download" };
  }

  async function exportStudentsCsv() {
    var data = await api("/api/admin/students");
    var list = data.students || [];
    var lines = ["ID,Насаб,Ном,Мактаб,Синф,Омӯзгор"];
    list.forEach(function (s) {
      lines.push([s.id,s.lastName,s.firstName,s.school,s.className,s.teacher].map(function (v) {
        var x = String(v==null?"":v); return /[",\n]/.test(x) ? '"'+x.replace(/"/g,'""')+'"' : x;
      }).join(","));
    });
    forceDownload("students.csv", "\ufeff" + lines.join("\r\n"), "text/csv;charset=utf-8");
  }

  async function registerStudent(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (_regLock) return false;
    _regLock = true;
    var msg = document.getElementById("studentFormMsg") || document.getElementById("studentMsg");
    if (msg) msg.classList.add("hidden");
    function val(id) {
      var el = document.getElementById(id);
      return el && el.value != null ? String(el.value).trim() : "";
    }
    var lastName = val("stLastName");
    var firstName = val("stFirstName");
    var patronymic = val("stFatherName") || val("stPatronymic");
    var birthDate = val("stBirthDate");
    var address = val("stAddress");
    var className = val("stClass") || val("stClassName");
    var school = val("stSchool");
    var teacher = val("stTeacher");
    var photoData = val("stPhotoData");
    var fullName = [lastName, firstName, patronymic].filter(Boolean).join(" ");
    try {
      if (!lastName || !firstName) throw new Error("Насаб ва Ном ҳатмӣ.");
      if (!className || !school) throw new Error("Синф ва Мактаб ҳатмӣ.");
      var data = await api("/api/admin/students", {
        method: "POST",
        body: JSON.stringify({
          lastName: lastName, firstName: firstName, patronymic: patronymic,
          birthDate: birthDate, address: address, className: className,
          school: school, teacher: teacher, photoData: photoData, fullName: fullName
        })
      });
      var s = data.student || data;
      Object.assign(s, { lastName: s.lastName||lastName, firstName: s.firstName||firstName,
        patronymic: s.patronymic||patronymic, school: s.school||school, className: s.className||className,
        teacher: s.teacher||teacher, photoData: photoData||s.photoData||"", fullName: s.fullName||fullName });
      var box = document.getElementById("newIdBox");
      if (box) box.classList.remove("hidden");
      var nv = document.getElementById("newIdValue");
      if (nv) nv.textContent = s.id || "";
      await saveStudentLocalCopy(s);
      if (msg) { msg.textContent = "ID сохта шуд."; msg.classList.remove("hidden","error"); msg.classList.add("ok"); }
      var formEl = document.getElementById("studentForm");
      if (formEl) formEl.reset();
      clearPhoto(); loadStudentsLocal();
    } catch (err) {
      if (msg) { msg.textContent = err.message || String(err); msg.classList.remove("hidden"); msg.classList.add("error"); }
      else alert(err.message || String(err));
    } finally { _regLock = false; }
    return false;
  }
  window.__geoRegisterStudent = registerStudent;
  window.__geoExportStudents = exportStudentsCsv;
  window.__geoPickStudentsFolder = pickStudentsFolder;

  function bind() {
    var form = document.getElementById("studentForm");
    if (form) {
      form.setAttribute("action", "javascript:void(0)");
      form.onsubmit = function (e) { e.preventDefault(); registerStudent(e); return false; };
    }
    var btnReg = document.getElementById("btnRegisterStudent");
    if (btnReg) { btnReg.type = "button"; btnReg.onclick = function (e) { e.preventDefault(); registerStudent(e); }; }
    var exportBtn = document.getElementById("exportStudentsBtn");
    if (exportBtn) exportBtn.onclick = function (e) { e.preventDefault(); exportStudentsCsv().catch(function (err) { alert(err.message||err); }); };
    var pickBtn = document.getElementById("btnPickStudentsFolder");
    if (pickBtn) pickBtn.onclick = function (e) { e.preventDefault(); pickStudentsFolder(); };
    var copyBtn = document.getElementById("copyIdBtn");
    if (copyBtn) copyBtn.onclick = async function () {
      var v = (document.getElementById("newIdValue") || {}).textContent || "";
      if (!v) return;
      try { await navigator.clipboard.writeText(v); alert("ID нусха шуд"); } catch (_) { prompt("Нусха:", v); }
    };
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") {
          loadStudentsLocal();
          listCameras().catch(function () {});
          tryRestoreDir().then(function (d) { updateFolderStatus(!!d); });
        }
      });
    });
    tryRestoreDir().then(function (d) { updateFolderStatus(!!d); });
    bindCamera();
  }

  async function loadStudentsLocal() {
    try {
      var data = await api("/api/admin/students");
      var body = document.getElementById("studentsBody");
      if (!body) return;
      var list = data.students || [];
      body.innerHTML = list.length ? list.map(function (s) {
        return "<tr><td><code>" + esc(s.id) + "</code></td><td>" + esc(s.fullName||"") + "</td><td>" + esc(s.className) +
          "</td><td>" + esc(s.school) + "</td><td>" + esc(s.teacher||"") + "</td><td>" + (s.hasPhoto?"✓":"—") +
          '</td><td><button type="button" class="btn small danger" data-del-student="' + esc(s.id) + '">Нест</button></td></tr>';
      }).join("") : '<tr><td colspan="7">Хонанда нест</td></tr>';
      body.querySelectorAll("[data-del-student]").forEach(function (btn) {
        btn.addEventListener("click", async function () {
          if (!confirm("Нест?")) return;
          await api("/api/admin/students/" + btn.dataset.delStudent, { method: "DELETE" });
          loadStudentsLocal();
        });
      });
    } catch (e) { console.warn(e); }
  }

  window.loadStudents = loadStudentsLocal;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
