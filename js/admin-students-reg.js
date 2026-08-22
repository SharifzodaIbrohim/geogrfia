/* Student registration + camera + local folder card + professional Даватнома */
(function () {
  const TOKEN_KEY = "geo_admin_token";
  const DIR_DB = "geografia_admin_fs";
  const DIR_STORE = "handles";
  const DIR_KEY = "students_info_dir";
  var _regLock = false;
  var _dirMemory = null;
  var _camStream = null;

  const esc = window.esc || function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      if (c === "&") return "&" + "amp;";
      if (c === "<") return "&" + "lt;";
      if (c === ">") return "&" + "gt;";
      if (c === '"') return "&" + "quot;";
      return "&#39;";
    });
  };

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem("adminToken") || "";
  }

  async function api(path, options) {
    options = options || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = getToken();
    if (token) headers["X-Admin-Token"] = token;
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(path, Object.assign({}, options, { headers: headers, credentials: "include" }));
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.error || data.message || ("Хато " + res.status));
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
        camStatus("Камера ёфт нашуд", true);
        return [];
      }
      cams.forEach(function (d, i) {
        var opt = document.createElement("option");
        opt.value = d.deviceId || "";
        opt.textContent = d.label || ("Камера " + (i + 1));
        sel.appendChild(opt);
      });
      camStatus(cams.length + " камера омода", false);
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
    if (!video) return;
    if (!secureContextOk()) { camStatus("HTTPS лозим аст", true); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return;
    stopCamera();
    var attempts = [];
    if (sel && sel.value) {
      attempts.push({ audio: false, video: { deviceId: { exact: sel.value } } });
    }
    attempts.push({ audio: false, video: { facingMode: "user" } });
    attempts.push({ audio: false, video: true });
    var lastErr = null;
    for (var i = 0; i < attempts.length; i++) {
      try {
        _camStream = await navigator.mediaDevices.getUserMedia(attempts[i]);
        video.srcObject = _camStream;
        video.style.display = "block";
        video.muted = true;
        try { await video.play(); } catch (_) {}
        camStatus("Камера фаъол", false);
        return;
      } catch (e) { lastErr = e; }
    }
    camStatus("Камера: " + ((lastErr && lastErr.message) || lastErr), true);
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
      camStatus("Аввал «Камера»", true);
      return;
    }
    var w = video.videoWidth || 640, h = video.videoHeight || 480;
    var scale = Math.min(1, 800 / Math.max(w, h));
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    applyPhoto(canvas.toDataURL("image/jpeg", 0.92));
    camStatus("Акс гирифта шуд", false);
  }

  function bindCamera() {
    var a = document.getElementById("btnStartCamera");
    var b = document.getElementById("btnCapturePhoto");
    var c = document.getElementById("btnClearPhoto");
    var d = document.getElementById("btnStopCamera");
    var f = document.getElementById("photoFileInput");
    if (a) { a.type = "button"; a.onclick = function (e) { e.preventDefault(); startCamera(); }; }
    if (b) { b.type = "button"; b.onclick = function (e) { e.preventDefault(); capturePhoto(); }; }
    if (c) { c.type = "button"; c.onclick = function (e) { e.preventDefault(); clearPhoto(); stopCamera(); }; }
    if (d) { d.type = "button"; d.onclick = function (e) { e.preventDefault(); stopCamera(); }; }
    if (f) {
      f.onchange = function (ev) {
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;
        var r = new FileReader();
        r.onload = function () { applyPhoto(r.result); };
        r.readAsDataURL(file);
      };
    }
    listCameras().catch(function () {});
  }

  function safeFileName(s) {
    return String(s || "student").replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_").slice(0, 80);
  }

  function buildStudentCardHtml(st) {
    var id = st.id || "";
    var full = st.fullName || [st.lastName, st.firstName, st.patronymic].filter(Boolean).join(" ");
    var photo = st.photoData || "";
    var genderLabel = st.gender === "male" ? "Мард" : (st.gender === "female" ? "Зан" : (st.gender || "—"));
    var olyTitle = st.olympiadTitle || "—";
    var olyStart = st.olympiadStart || "—";
    var webUrl = "https://geografia-19tf.onrender.com";
    var igUrl = "https://www.instagram.com/geografia.tj/";
    var webQr = "https://api.qrserver.com/v1/create-qr-code/?size=140x140&margin=8&data=" + encodeURIComponent(webUrl);
    var igQr = "https://api.qrserver.com/v1/create-qr-code/?size=140x140&margin=8&data=" + encodeURIComponent(igUrl);
    var photoBlock = photo
      ? '<div class="photo-wrap"><img src="' + photo + '" alt="photo"/></div>'
      : '<div class="photo-wrap placeholder">Бе сурат</div>';
    var rows = [
      ["ID (барои воридшавӣ)", id],
      ["Насаб", st.lastName || ""],
      ["Ном", st.firstName || ""],
      ["Номи падар", st.patronymic || ""],
      ["Ҷинс", genderLabel],
      ["Таваллуд", st.birthDate || ""],
      ["Суроға", st.address || ""],
      ["Муассиса / Мактаб", st.school || ""],
      ["Синф", st.className || ""],
      ["Омӯзгор", st.teacher || ""],
      ["Унвони олимпиада", olyTitle],
      ["Санаи оғози олимпиада", olyStart],
      ["Санаи бақайдгирӣ", st.createdAt || st.registeredAt || new Date().toLocaleString()]
    ];
    var table = rows.map(function (r) {
      return "<tr><th>" + esc(r[0]) + "</th><td>" + esc(r[1]) + "</td></tr>";
    }).join("");
    var subLine = olyTitle !== "—" ? olyTitle : "Иштирокчӣ · Geografia.tj";
    return "<!DOCTYPE html><html lang=\"tg\"><head><meta charset=\"utf-8\"/>" +
      "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>" +
      "<title>Даватнома — " + esc(full) + " | Geografia.tj</title>" +
      "<style>" +
      ":root{--g1:#0b3d2e;--g2:#1a7a5c;--g3:#c8f0dc;--accent:#e8a017;--ink:#14221c;--muted:#5a6b62;--line:#d5e4db}" +
      "*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:linear-gradient(160deg,#eef6f1,#f7faf8 40%,#fff);color:var(--ink)}" +
      ".page{max-width:820px;margin:20px auto;padding:12px}" +
      ".toolbar{margin-bottom:12px}.toolbar button{border:0;background:var(--g2);color:#fff;padding:10px 16px;border-radius:10px;font-weight:600;cursor:pointer}" +
      ".pass{background:#fff;border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 12px 40px rgba(11,61,46,.08)}" +
      ".head{background:linear-gradient(135deg,var(--g1),var(--g2));color:#fff;padding:22px 24px 18px}" +
      ".brand{font-size:.95rem;letter-spacing:.18em;opacity:.9;font-weight:700}" +
      ".badge{display:inline-block;margin-top:10px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);padding:6px 14px;border-radius:999px;font-weight:700;letter-spacing:.06em}" +
      ".head h1{margin:12px 0 4px;font-size:1.65rem;font-weight:800}.head p{margin:0;opacity:.9}" +
      ".accent-bar{height:5px;background:linear-gradient(90deg,var(--accent),#f3d27a,var(--accent))}" +
      ".body{padding:22px 24px 8px}.top{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}" +
      ".photo-wrap{width:150px;height:150px;border-radius:14px;overflow:hidden;border:3px solid var(--g3);background:#f3f7f5;flex-shrink:0}" +
      ".photo-wrap img{width:100%;height:100%;object-fit:cover;display:block}" +
      ".photo-wrap.placeholder{display:flex;align-items:center;justify-content:center;color:var(--muted)}" +
      ".meta{flex:1;min-width:220px}" +
      ".idbox{display:inline-block;font-family:ui-monospace,Consolas,monospace;font-size:1.15rem;letter-spacing:1px;background:var(--g1);color:#fff;padding:10px 14px;border-radius:10px;margin:4px 0 10px}" +
      ".name{font-size:1.35rem;font-weight:800;margin:0 0 6px}.sub{color:var(--muted);margin:0}" +
      "table{width:100%;border-collapse:collapse;margin:20px 0 8px;font-size:14px}" +
      "th,td{padding:10px 12px;border:1px solid var(--line);text-align:left;vertical-align:top}" +
      "th{width:38%;background:#f3f8f5;color:var(--g1);font-weight:700}" +
      ".foot{margin-top:8px;padding:18px 24px 22px;border-top:1px dashed var(--line);background:linear-gradient(180deg,#fbfdfc,#f5faf7)}" +
      ".qr-row{display:flex;gap:28px;flex-wrap:wrap;justify-content:center}.qr{text-align:center;width:160px}" +
      ".qr img{width:140px;height:140px;border-radius:12px;border:1px solid var(--line);background:#fff;padding:6px}" +
      ".qr .lbl{margin-top:8px;font-size:.82rem;font-weight:700;color:var(--g1)}.qr .url{font-size:.72rem;color:var(--muted);word-break:break-all}" +
      ".note{text-align:center;margin:16px 0 0;color:var(--muted);font-size:.85rem}" +
      ".seal{text-align:center;margin-top:10px;font-weight:700;color:var(--g2);letter-spacing:.04em}" +
      "@media print{body{background:#fff}.toolbar{display:none!important}.page{margin:0;padding:0;max-width:none}.pass{box-shadow:none;border-radius:0}}" +
      "</style></head><body><div class=\"page\">" +
      "<div class=\"toolbar\"><button onclick=\"window.print()\">Чоп / Save as PDF</button></div>" +
      "<article class=\"pass\"><header class=\"head\">" +
      "<div class=\"brand\">GEOGRAFIA.TJ</div>" +
      "<div class=\"badge\">ДАВАТНОМА · ИҶОЗАТНОМА</div>" +
      "<h1>Даватномаи иштирокчӣ</h1>" +
      "<p>Ҳуҷҷати расмии бақайдгирӣ барои олимпиада / викторина</p>" +
      "</header><div class=\"accent-bar\"></div><div class=\"body\">" +
      "<div class=\"top\">" + photoBlock +
      "<div class=\"meta\"><div class=\"idbox\">" + esc(id) + "</div>" +
      "<p class=\"name\">" + esc(full) + "</p>" +
      "<p class=\"sub\">" + esc(subLine) + "</p></div></div>" +
      "<table>" + table + "</table></div>" +
      "<footer class=\"foot\"><div class=\"qr-row\">" +
      "<div class=\"qr\"><img src=\"" + igQr + "\" alt=\"Instagram QR\"/><div class=\"lbl\">Instagram</div><div class=\"url\">instagram.com/geografia.tj</div></div>" +
      "<div class=\"qr\"><img src=\"" + webQr + "\" alt=\"Web QR\"/><div class=\"lbl\">Веб-саҳифа</div><div class=\"url\">" + esc(webUrl) + "</div></div>" +
      "</div><p class=\"seal\">GEOGRAFIA.TJ · Платформаи география</p>" +
      "<p class=\"note\">Ин даватнома барои воридшавӣ ба платформа ва иштирок дар олимпиада пешбинӣ шудааст. ID-ро нигоҳ доред.</p>" +
      "</footer></article></div></body></html>";
  }

  function buildStudentTxt(st) {
    var full = st.fullName || [st.lastName, st.firstName, st.patronymic].filter(Boolean).join(" ");
    var genderLabel = st.gender === "male" ? "Мард" : (st.gender === "female" ? "Зан" : (st.gender || ""));
    return [
      "ДАВАТНОМА — Geografia.tj",
      "ID: " + (st.id || ""),
      "Ном: " + full,
      "Ҷинс: " + genderLabel,
      "Мактаб: " + (st.school || ""),
      "Синф: " + (st.className || ""),
      "Олимпиада: " + (st.olympiadTitle || ""),
      "Санаи оғоз: " + (st.olympiadStart || ""),
      "Веб: https://geografia-19tf.onrender.com",
      "Instagram: https://www.instagram.com/geografia.tj/"
    ].join("\n");
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
      var perm = await handle.queryPermission({ mode: "readwrite" });
      if (perm === "granted") { _dirMemory = handle; return handle; }
      perm = await handle.requestPermission({ mode: "readwrite" });
      if (perm === "granted") { _dirMemory = handle; return handle; }
    } catch (_) {}
    return null;
  }

  async function pickStudentsFolder() {
    if (!window.showDirectoryPicker) {
      alert("Барои папка Chrome ё Edge лозим аст.");
      return null;
    }
    try {
      var handle = await window.showDirectoryPicker({ id: "geografia-students-info", mode: "readwrite", startIn: "documents" });
      _dirMemory = handle;
      await idbSet(DIR_KEY, handle);
      updateFolderStatus(true, handle.name || "папка");
      return handle;
    } catch (e) {
      if (!(e && e.name === "AbortError")) alert("Папка: " + (e && e.message ? e.message : e));
      return null;
    }
  }

  function updateFolderStatus(ok, name) {
    var el = document.getElementById("localFolderStatus");
    if (!el) return;
    el.textContent = ok ? ("Папка пайваст" + (name ? (" — " + name) : "")) : "Папка интихоб нашудааст";
    el.style.color = ok ? "#8fd4a8" : "#ffb86b";
  }

  async function saveStudentLocalCopy(st) {
    var html = buildStudentCardHtml(st);
    var txt = buildStudentTxt(st);
    var base = safeFileName((st.lastName || "") + "_" + (st.firstName || "") + "_" + (st.id || "")) || "student";
    var dir = _dirMemory || (await tryRestoreDir());
    if (!dir) {
      var ok = confirm("Папкаи «Малумотхои хонандагон»-ро интихоб кунед.");
      if (!ok) return { ok: false, mode: "cancelled" };
      dir = await pickStudentsFolder();
      if (!dir) return { ok: false, mode: "no-folder" };
    }
    try {
      await writeFileToDir(dir, base + ".html", html, "text/html;charset=utf-8");
      await writeFileToDir(dir, base + ".txt", txt, "text/plain;charset=utf-8");
      updateFolderStatus(true, dir.name || "");
      return { ok: true, mode: "folder", name: base };
    } catch (e) {
      alert("Захира нашуд: " + (e && e.message ? e.message : e));
      return { ok: false, mode: "fail" };
    }
  }

  async function exportStudentsCsv() {
    var data = await api("/api/admin/students");
    var list = data.students || [];
    var lines = ["ID,Насаб,Ном,Номи падар,Ҷинс,Таваллуд,Суроға,Мактаб,Синф,Омӯзгор,Олимпиада,Санаи оғоз"];
    list.forEach(function (s) {
      lines.push([s.id, s.lastName, s.firstName, s.patronymic, s.gender, s.birthDate, s.address, s.school, s.className, s.teacher, s.olympiadTitle, s.olympiadStart].map(function (v) {
        var x = String(v == null ? "" : v);
        return /[",\n]/.test(x) ? '"' + x.replace(/"/g, '""') + '"' : x;
      }).join(","));
    });
    var blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = "students.csv"; a.style.display = "none";
    document.body.appendChild(a); a.click();
    setTimeout(function () { try { URL.revokeObjectURL(url); } catch (_) {} a.remove(); }, 1500);
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
    var gender = val("stGender");
    var olympiadTitle = val("stOlympiadTitle");
    var olympiadStart = val("stOlympiadStart");
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
          school: school, teacher: teacher, gender: gender,
          olympiadTitle: olympiadTitle, olympiadStart: olympiadStart,
          photoData: photoData, fullName: fullName
        })
      });
      var s = data.student || data;
      Object.assign(s, {
        lastName: s.lastName || lastName,
        firstName: s.firstName || firstName,
        patronymic: s.patronymic || patronymic,
        birthDate: s.birthDate || birthDate,
        address: s.address || address,
        school: s.school || school,
        className: s.className || className,
        teacher: s.teacher || teacher,
        gender: gender || s.gender || "",
        olympiadTitle: olympiadTitle || s.olympiadTitle || "",
        olympiadStart: olympiadStart || s.olympiadStart || "",
        photoData: photoData || s.photoData || "",
        fullName: s.fullName || fullName,
        createdAt: s.createdAt || new Date().toLocaleString()
      });
      var box = document.getElementById("newIdBox");
      if (box) box.classList.remove("hidden");
      var nv = document.getElementById("newIdValue");
      if (nv) nv.textContent = s.id || "";
      var saved = await saveStudentLocalCopy(s);
      var extra = "";
      if (saved && saved.ok) extra = " · файл: " + (saved.name || "") + ".html";
      if (msg) {
        msg.textContent = "ID сохта шуд: " + (s.id || "") + extra;
        msg.classList.remove("hidden", "error");
        msg.classList.add("ok");
      }
      var formEl = document.getElementById("studentForm");
      if (formEl) formEl.reset();
      clearPhoto();
      loadStudentsLocal();
    } catch (err) {
      if (msg) {
        msg.textContent = err.message || String(err);
        msg.classList.remove("hidden");
        msg.classList.add("error");
      } else alert(err.message || String(err));
    } finally {
      _regLock = false;
    }
    return false;
  }
  window.__geoRegisterStudent = registerStudent;
  window.__geoExportStudents = exportStudentsCsv;
  window.__geoPickStudentsFolder = pickStudentsFolder;

  async function deleteStudent(id) {
    id = String(id || "").trim();
    if (!id) return;
    if (!confirm("Хонандаро нест кунем?\nID: " + id)) return;
    try {
      await api("/api/admin/students/" + encodeURIComponent(id), { method: "DELETE" });
      loadStudentsLocal();
    } catch (err) {
      alert("Нест нашуд: " + (err.message || err));
    }
  }

  function bind() {
    var form = document.getElementById("studentForm");
    if (form) {
      form.setAttribute("action", "javascript:void(0)");
      form.onsubmit = function (e) { e.preventDefault(); registerStudent(e); return false; };
    }
    var btnReg = document.getElementById("btnRegisterStudent");
    if (btnReg) {
      btnReg.type = "button";
      btnReg.onclick = function (e) { e.preventDefault(); registerStudent(e); };
    }
    var exportBtn = document.getElementById("exportStudentsBtn");
    if (exportBtn) {
      exportBtn.onclick = function (e) {
        e.preventDefault();
        exportStudentsCsv().catch(function (err) { alert(err.message || err); });
      };
    }
    var pickBtn = document.getElementById("btnPickStudentsFolder");
    if (pickBtn) {
      pickBtn.onclick = function (e) { e.preventDefault(); pickStudentsFolder(); };
    }
    var copyBtn = document.getElementById("copyIdBtn");
    if (copyBtn) {
      copyBtn.onclick = async function () {
        var v = (document.getElementById("newIdValue") || {}).textContent || "";
        if (!v) return;
        try { await navigator.clipboard.writeText(v); alert("ID нусха шуд"); }
        catch (_) { prompt("Нусха:", v); }
      };
    }
    var body = document.getElementById("studentsBody");
    if (body && !body._geoDelBound) {
      body._geoDelBound = true;
      body.addEventListener("click", function (ev) {
        var btn = ev.target && ev.target.closest ? ev.target.closest("[data-del-student]") : null;
        if (!btn) return;
        ev.preventDefault();
        deleteStudent(btn.getAttribute("data-del-student"));
      });
    }
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (btn.dataset.tab === "students") {
          loadStudentsLocal();
          listCameras().catch(function () {});
          tryRestoreDir().then(function (d) { updateFolderStatus(!!d, d && d.name); });
        }
      });
    });
    tryRestoreDir().then(function (d) { updateFolderStatus(!!d, d && d.name); });
    bindCamera();
    loadStudentsLocal();
  }

  async function loadStudentsLocal() {
    try {
      var data = await api("/api/admin/students");
      var body = document.getElementById("studentsBody");
      if (!body) return;
      var list = data.students || [];
      body.innerHTML = list.length ? list.map(function (s) {
        var id = s.id || "";
        return "<tr>" +
          "<td><code>" + esc(id) + "</code></td>" +
          "<td>" + esc(s.fullName || [s.lastName, s.firstName].filter(Boolean).join(" ")) + "</td>" +
          "<td>" + esc(s.className || "") + "</td>" +
          "<td>" + esc(s.school || "") + "</td>" +
          "<td>" + esc(s.teacher || "") + "</td>" +
          "<td>" + (s.hasPhoto || s.photoData ? "+" : "-") + "</td>" +
          "<td><button type=\"button\" class=\"btn small danger\" data-del-student=\"" + esc(id) + "\">Нест</button></td>" +
          "</tr>";
      }).join("") : '<tr><td colspan="7">Хонанда нест</td></tr>';
    } catch (e) {
      console.warn("loadStudents", e);
    }
  }

  window.loadStudents = loadStudentsLocal;
  window.__geoDeleteStudent = deleteStudent;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
