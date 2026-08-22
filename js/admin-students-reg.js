/* Student reg + camera + CSV + folder */
(function () {
  var TOKEN_KEY = "geo_admin_token";
  var DIR_DB = "geografia_admin_fs";
  var DIR_STORE = "handles";
  var DIR_KEY = "students_info_dir";
  var _regLock = false;
  var _dirMemory = null;
  var _camStream = null;

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&" + "amp;")
      .replace(/</g, "&" + "lt;")
      .replace(/>/g, "&" + "gt;")
      .replace(/"/g, "&" + "quot;")
      .replace(/'/g, "&#" + "39;");
  }
  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem("adminToken") || "";
  }
  async function api(path, options) {
    options = options || {};
    var headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    var token = getToken();
    if (token) {
      headers["X-Admin-Token"] = token;
      headers["Authorization"] = "Bearer " + token;
    }
    var res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: "include" }));
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.message || ("Хато " + res.status));
    return data;
  }
  function val(id) {
    var el = document.getElementById(id);
    return el && el.value != null ? String(el.value).trim() : "";
  }
  function applyPhoto(dataUrl) {
    var hidden = document.getElementById("stPhotoData");
    var img = document.getElementById("photoImg");
    var ph = document.getElementById("photoPlaceholder");
    if (hidden) hidden.value = dataUrl || "";
    if (img && dataUrl) { img.src = dataUrl; img.style.display = "block"; }
    else if (img) { img.removeAttribute("src"); img.style.display = "none"; }
    if (ph) ph.style.display = dataUrl ? "none" : "";
  }
  function clearPhoto() {
    applyPhoto("");
    var f = document.getElementById("photoFileInput");
    if (f) f.value = "";
  }
  function setCamStatus(msg) {
    var el = document.getElementById("cameraStatus");
    if (el) el.textContent = msg || "";
  }
  async function listCameras() {
    var sel = document.getElementById("cameraSelect");
    if (!sel || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
      var devices = await navigator.mediaDevices.enumerateDevices();
      var cams = devices.filter(function (d) { return d.kind === "videoinput"; });
      sel.innerHTML = "";
      if (!cams.length) { sel.innerHTML = '<option value="">Камера ёфт нашуд</option>'; return; }
      cams.forEach(function (d, i) {
        var o = document.createElement("option");
        o.value = d.deviceId || "";
        o.textContent = d.label || ("Камера " + (i + 1));
        sel.appendChild(o);
      });
    } catch (e) { setCamStatus("Рӯйхати камера: " + (e.message || e)); }
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
    try {
      setCamStatus("Кушода истодааст…");
      _camStream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = _camStream;
      video.style.display = "block";
      await video.play().catch(function () {});
      setCamStatus("Камера фаъол");
      await listCameras();
    } catch (e) {
      setCamStatus("Хато: " + (e.message || e));
      _camStream = null;
    }
  }
  function stopCamera() {
    if (_camStream) {
      try { _camStream.getTracks().forEach(function (t) { t.stop(); }); } catch (_) {}
      _camStream = null;
    }
    var video = document.getElementById("cameraVideo");
    if (video) { video.srcObject = null; video.style.display = "none"; }
    setCamStatus("");
  }
  function capturePhoto() {
    var video = document.getElementById("cameraVideo");
    var canvas = document.getElementById("cameraCanvas");
    if (!video || !canvas || !video.srcObject || video.videoWidth < 2) {
      setCamStatus("Аввал камераро кушоед"); return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    applyPhoto(canvas.toDataURL("image/jpeg", 0.88));
    setCamStatus("Акс гирифта шуд");
  }
  function idbOpen() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DIR_DB, 1);
      req.onupgradeneeded = function () {
        if (!req.result.objectStoreNames.contains(DIR_STORE)) req.result.createObjectStore(DIR_STORE);
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }
  async function idbSet(key, val) {
    var db = await idbOpen();
    return new Promise(function (resolve, reject) {
      var tx = db.transaction(DIR_STORE, "readwrite");
      tx.objectStore(DIR_STORE).put(val, key);
      tx.oncomplete = function () { resolve(); };
      tx.onerror = function () { reject(tx.error); };
    });
  }
  async function idbGet(key) {
    var db = await idbOpen();
    return new Promise(function (resolve, reject) {
      var req = db.transaction(DIR_STORE, "readonly").objectStore(DIR_STORE).get(key);
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }
  function updateFolderStatus(ok, name) {
    var el = document.getElementById("localFolderStatus");
    if (!el) return;
    el.textContent = ok ? ("📁 " + (name || "папка")) : (name || "");
    el.style.color = ok ? "var(--accent, #70db97)" : "";
  }
  async function tryRestoreDir() {
    try {
      if (!window.showDirectoryPicker) return null;
      var handle = await idbGet(DIR_KEY);
      if (!handle) return null;
      if (handle.queryPermission) {
        var perm = await handle.queryPermission({ mode: "readwrite" });
        if (perm !== "granted") {
          perm = await handle.requestPermission({ mode: "readwrite" });
          if (perm !== "granted") return null;
        }
      }
      _dirMemory = handle;
      updateFolderStatus(true, handle.name || "папка");
      return handle;
    } catch (_) { return null; }
  }
  async function pickStudentsFolder() {
    if (!window.showDirectoryPicker) {
      alert("Chrome/Edge лозим барои папкаи маҳаллӣ."); return;
    }
    try {
      var handle = await window.showDirectoryPicker({ mode: "readwrite" });
      _dirMemory = handle;
      await idbSet(DIR_KEY, handle);
      updateFolderStatus(true, handle.name || "папка");
    } catch (e) {
      if (e && e.name === "AbortError") return;
      alert("Папка: " + (e.message || e));
    }
  }
  function csvEscape(v) {
    var s = String(v == null ? "" : v);
    if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }
  async function exportStudentsCsv() {
    try {
      var data = await api("/api/admin/students");
      var list = data.students || [];
      var headers = ["ID","Насаб","Ном","Номи падар","Ҷинс","Таваллуд","Суроға","Мактаб","Синф","Омӯзгор","Олимпиада","Санаи оғоз","Сурат"];
      var lines = [headers.join(",")];
      list.forEach(function (s) {
        var g = s.gender === "male" ? "Мард" : (s.gender === "female" ? "Зан" : (s.gender || ""));
        lines.push([s.id,s.lastName,s.firstName,s.patronymic,g,s.birthDate,s.address,s.school,s.className,s.teacher,s.olympiadTitle,s.olympiadStart,(s.hasPhoto||s.photoData)?"ҳа":"не"].map(csvEscape).join(","));
      });
      var blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = "students_" + new Date().toISOString().slice(0,10) + ".csv";
      document.body.appendChild(a); a.click();
      setTimeout(function () { try { URL.revokeObjectURL(url); } catch (_) {} a.remove(); }, 1500);
    } catch (e) { alert("Export: " + (e.message || e)); }
  }
  async function registerStudent(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (_regLock) return false;
    _regLock = true;
    var msg = document.getElementById("studentFormMsg");
    if (msg) msg.classList.add("hidden");
    var lastName = val("stLastName"), firstName = val("stFirstName");
    var patronymic = val("stFatherName"), birthDate = val("stBirthDate");
    var address = val("stAddress"), className = val("stClass"), school = val("stSchool");
    var teacher = val("stTeacher"), gender = val("stGender");
    var olympiadTitle = val("stOlympiadTitle"), olympiadStart = val("stOlympiadStart");
    var photoData = val("stPhotoData");
    var fullName = [lastName, firstName, patronymic].filter(Boolean).join(" ");
    try {
      if (!lastName || !firstName) throw new Error("Насаб ва Ном ҳатмӣ.");
      if (!className || !school) throw new Error("Синф ва Мактаб ҳатмӣ.");
      if (!getToken()) throw new Error("Аввал ворид шавед (token нест). Саҳифаро нав кунед ва дубора login кунед.");
      var data = await api("/api/admin/students", {
        method: "POST",
        body: JSON.stringify({
          lastName: lastName, firstName: firstName, patronymic: patronymic,
          birthDate: birthDate, address: address, className: className,
          school: school, teacher: teacher, gender: gender,
          olympiadTitle: olympiadTitle, olympiadStart: olympiadStart,
          photoData: photoData, fullName: fullName
        })
      });
      var s = data.student || data;
      var box = document.getElementById("newIdBox");
      if (box) box.classList.remove("hidden");
      var nv = document.getElementById("newIdValue");
      if (nv) nv.textContent = s.id || "";
      if (msg) {
        msg.textContent = "ID: " + (s.id || "") + " · Сабт шуд";
        msg.classList.remove("hidden", "error");
        msg.classList.add("ok");
      }
      var formEl = document.getElementById("studentForm");
      if (formEl) formEl.reset();
      clearPhoto(); stopCamera();
      loadStudentsLocal();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message || String(err);
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(err.message || String(err));
    } finally { _regLock = false; }
    return false;
  }
  async function loadStudentsLocal() {
    try {
      var data = await api("/api/admin/students");
      var body = document.getElementById("studentsBody");
      if (!body) return;
      var list = data.students || [];
      body.innerHTML = list.length ? list.map(function (s) {
        var id = s.id || "";
        var g = s.gender === "male" ? "Мард" : (s.gender === "female" ? "Зан" : (s.gender || "—"));
        return "<tr><td><code>" + esc(id) + "</code></td><td>" + esc(s.fullName || "") + "</td><td>" + esc(g) +
          "</td><td>" + esc(s.className || "") + "</td><td>" + esc(s.school || "") +
          "</td><td>" + esc(s.olympiadTitle || "—") + "</td><td>" + (s.hasPhoto || s.photoData ? "+" : "-") +
          "</td><td><button type=\"button\" class=\"btn small danger\" data-del-student=\"" + esc(id) + "\">Нест</button></td></tr>";
      }).join("") : '<tr><td colspan="8">Хонанда нест</td></tr>';
    } catch (e) {
      var body = document.getElementById("studentsBody");
      if (body) body.innerHTML = '<tr><td colspan="8">Хато: ' + esc(e.message || e) + "</td></tr>";
    }
  }
  async function deleteStudent(id) {
    id = String(id || "").trim();
    if (!id || !confirm("Нест кунем?\n" + id)) return;
    try {
      await api("/api/admin/students/" + encodeURIComponent(id), { method: "DELETE" });
      loadStudentsLocal();
    } catch (err) { alert("Нест нашуд: " + (err.message || err)); }
  }
  function onClick(id, fn) {
    var el = document.getElementById(id);
    if (!el) { console.warn("[students-reg] missing #" + id); return; }
    el.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      try { fn(e); } catch (err) {
        console.error("[students-reg]", id, err);
        alert((err && err.message) || String(err));
      }
    });
  }
  function bind() {
    console.log("[students-reg] bind OK");
    var form = document.getElementById("studentForm");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        registerStudent(e);
        return false;
      });
    }
    onClick("btnRegisterStudent", registerStudent);
    onClick("exportStudentsBtn", exportStudentsCsv);
    onClick("btnPickStudentsFolder", pickStudentsFolder);
    onClick("btnStartCamera", startCamera);
    onClick("btnCapturePhoto", capturePhoto);
    onClick("btnStopCamera", stopCamera);
    onClick("btnClearPhoto", clearPhoto);
    var copyBtn = document.getElementById("copyIdBtn");
    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        var v = (document.getElementById("newIdValue") || {}).textContent || "";
        if (!v) return;
        try { await navigator.clipboard.writeText(v); alert("ID нусха шуд"); }
        catch (_) { prompt("Нусха:", v); }
      });
    }
    var body = document.getElementById("studentsBody");
    if (body && !body._geoDelBound) {
      body._geoDelBound = true;
      body.addEventListener("click", function (ev) {
        var btn = ev.target && ev.target.closest && ev.target.closest("[data-del-student]");
        if (!btn) return;
        deleteStudent(btn.getAttribute("data-del-student"));
      });
    }
    var f = document.getElementById("photoFileInput");
    if (f) {
      f.addEventListener("change", function (ev) {
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;
        var r = new FileReader();
        r.onload = function () { applyPhoto(r.result); };
        r.readAsDataURL(file);
      });
    }
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") loadStudentsLocal();
      });
    });
    listCameras();
    tryRestoreDir().then(function (d) { updateFolderStatus(!!d, d && d.name); });
    loadStudentsLocal();
  }
  window.__geoRegisterStudent = registerStudent;
  window.__geoExportStudents = exportStudentsCsv;
  window.__geoPickStudentsFolder = pickStudentsFolder;
  window.loadStudents = loadStudentsLocal;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();
